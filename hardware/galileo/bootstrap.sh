#!/usr/bin/env bash
# bootstrap.sh — One-command SkyHerd Galileo `edge-tank` bringup.
#
# Usage (on the Galileo itself, logged in as root via SSH or serial console):
#
#   bash /media/mmcblk0p1/bootstrap.sh
#
# Or, after scp'ing the file onto the Galileo:
#
#   bash bootstrap.sh
#
# Input: skyherd-galileo-credentials.json, default location
#          /boot/skyherd-galileo-credentials.json
#        (or /media/mmcblk0p1/skyherd-galileo-credentials.json — the same FAT32
#        boot partition, depending on Yocto mountpoint conventions.)
#        Override via env: SKYHERD_CREDS_FILE=/path/to/creds.json bash bootstrap.sh
#
# Supported flags:
#   --dry-run   Print the derived commands without executing.
#
# The script:
#   1. Validates credentials.json exists + is well-formed JSON (python3 -m json.tool).
#   2. Extracts mqtt/ranch/edge/mode fields with a small Python parser.
#   3. Installs Python 3 + paho-mqtt via opkg (idempotent).
#   4. Writes /etc/skyherd/galileo.env.
#   5. Installs + enables the skyherd-galileo.service systemd unit.
#
# Idempotent: safe to re-run. Prints "[SKIP]" for steps already done.

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SKYHERD_CREDS_FILE="${SKYHERD_CREDS_FILE:-/boot/skyherd-galileo-credentials.json}"
DRY_RUN=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

err() { echo "bootstrap.sh: $*" >&2; }
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf 'DRY-RUN: '
        printf '%q ' "$@"
        echo
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Step 1 — credentials.json (try a couple of common paths on Yocto)
# ---------------------------------------------------------------------------

if [ ! -f "$SKYHERD_CREDS_FILE" ]; then
    for alt in /media/mmcblk0p1/skyherd-galileo-credentials.json \
               /media/realroot/boot/skyherd-galileo-credentials.json \
               ./skyherd-galileo-credentials.json; do
        if [ -f "$alt" ]; then
            SKYHERD_CREDS_FILE="$alt"
            break
        fi
    done
fi

if [ ! -f "$SKYHERD_CREDS_FILE" ]; then
    err "credentials file not found."
    err "Tried: $SKYHERD_CREDS_FILE and common Yocto mountpoints."
    err "Drop skyherd-galileo-credentials.json on the microSD boot partition,"
    err "or set SKYHERD_CREDS_FILE=/path/to/creds.json."
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 2 — Parse fields (use python3 — Galileo images usually lack jq)
# ---------------------------------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    # Python 3 isn't installed yet — install it first, then parse.
    echo "python3 not found; installing via opkg before parsing creds..."
    run opkg update
    run opkg install python3 python3-modules
fi

read_field() {
    python3 - "$SKYHERD_CREDS_FILE" "$1" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
v = data.get(key, "")
print(v if v is not None else "")
PY
}

MQTT_URL="$(read_field mqtt_url)"
RANCH_ID="$(read_field ranch_id)"
EDGE_ID="$(read_field edge_id)"
SENSOR_MODE="$(read_field sensor_mode)"
PUBLISH_INTERVAL_SEC="$(read_field publish_interval_sec)"
HEARTBEAT_INTERVAL_SEC="$(read_field heartbeat_interval_sec)"

: "${SENSOR_MODE:=sim}"
: "${PUBLISH_INTERVAL_SEC:=60}"
: "${HEARTBEAT_INTERVAL_SEC:=30}"

MISSING=""
[ -z "$MQTT_URL" ] && MISSING="$MISSING mqtt_url"
[ -z "$RANCH_ID" ] && MISSING="$MISSING ranch_id"
[ -z "$EDGE_ID" ]  && MISSING="$MISSING edge_id"

if [ -n "$MISSING" ]; then
    err "missing required field(s):$MISSING"
    err "see hardware/galileo/credentials.example.json for the full schema."
    exit 2
fi

echo "============================================================"
echo " SkyHerd Galileo Bootstrap"
echo " creds_file           = $SKYHERD_CREDS_FILE"
echo " edge_id              = $EDGE_ID"
echo " ranch_id             = $RANCH_ID"
echo " mqtt_url             = $MQTT_URL"
echo " sensor_mode          = $SENSOR_MODE"
echo " publish_interval_sec = $PUBLISH_INTERVAL_SEC"
echo " heartbeat_interval_s = $HEARTBEAT_INTERVAL_SEC"
echo "============================================================"

# ---------------------------------------------------------------------------
# Step 3 — opkg packages
# ---------------------------------------------------------------------------

ensure_opkg_pkg() {
    local pkg="$1"
    if opkg list-installed 2>/dev/null | grep -q "^${pkg} "; then
        echo "  [SKIP] $pkg already installed"
        return 0
    fi
    echo "  [..] opkg install $pkg"
    run opkg install "$pkg" || {
        err "opkg install $pkg failed — is there internet on eth0?"
        return 1
    }
}

echo "--- opkg packages ---"
run opkg update
ensure_opkg_pkg python3 || true
ensure_opkg_pkg python3-modules || true
ensure_opkg_pkg python3-pip || true
ensure_opkg_pkg python3-paho-mqtt || true

# mraa only needed if sensor_mode=real; install opportunistically, don't fail.
if [ "$SENSOR_MODE" = "real" ]; then
    ensure_opkg_pkg mraa || true
    ensure_opkg_pkg python3-mraa || true
fi

# Fallback — pip install paho-mqtt if the opkg package was unavailable.
if ! python3 -c 'import paho.mqtt' 2>/dev/null; then
    echo "  [..] pip install paho-mqtt (fallback)"
    run python3 -m pip install --no-cache-dir paho-mqtt || true
fi

# ---------------------------------------------------------------------------
# Step 4 — Install files + write env
# ---------------------------------------------------------------------------

INSTALL_DIR="/opt/skyherd-galileo"
PUBLISHER_SRC=""
for cand in \
    /media/mmcblk0p1/sensor_publisher.py \
    "$(dirname "$SKYHERD_CREDS_FILE")/sensor_publisher.py" \
    ./sensor_publisher.py \
    "$(dirname "$0")/sensor_publisher.py"; do
    if [ -f "$cand" ]; then
        PUBLISHER_SRC="$cand"
        break
    fi
done

if [ -z "$PUBLISHER_SRC" ]; then
    err "sensor_publisher.py not found near bootstrap.sh."
    err "Copy it to the boot partition alongside bootstrap.sh."
    exit 2
fi

echo "--- installing publisher ---"
run mkdir -p "$INSTALL_DIR"
run install -m 0755 "$PUBLISHER_SRC" "$INSTALL_DIR/sensor_publisher.py"

echo "--- writing /etc/skyherd/galileo.env ---"
run mkdir -p /etc/skyherd
ENV_CONTENT=$(cat <<EOF
# /etc/skyherd/galileo.env — written by bootstrap.sh; safe to re-run.
MQTT_URL=$MQTT_URL
RANCH_ID=$RANCH_ID
EDGE_ID=$EDGE_ID
SENSOR_MODE=$SENSOR_MODE
PUBLISH_INTERVAL_SEC=$PUBLISH_INTERVAL_SEC
HEARTBEAT_INTERVAL_SEC=$HEARTBEAT_INTERVAL_SEC
EOF
)
if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: would write /etc/skyherd/galileo.env with:"
    printf '%s\n' "$ENV_CONTENT"
else
    printf '%s\n' "$ENV_CONTENT" > /etc/skyherd/galileo.env
    chmod 0640 /etc/skyherd/galileo.env
fi

# ---------------------------------------------------------------------------
# Step 5 — systemd unit
# ---------------------------------------------------------------------------

SERVICE_SRC=""
for cand in \
    /media/mmcblk0p1/skyherd-galileo.service \
    "$(dirname "$SKYHERD_CREDS_FILE")/skyherd-galileo.service" \
    ./skyherd-galileo.service \
    "$(dirname "$0")/skyherd-galileo.service"; do
    if [ -f "$cand" ]; then
        SERVICE_SRC="$cand"
        break
    fi
done

if [ -z "$SERVICE_SRC" ]; then
    err "skyherd-galileo.service not found near bootstrap.sh."
    exit 2
fi

echo "--- installing systemd unit ---"
run install -m 0644 "$SERVICE_SRC" /etc/systemd/system/skyherd-galileo.service
run systemctl daemon-reload
run systemctl enable skyherd-galileo.service
run systemctl restart skyherd-galileo.service

# ---------------------------------------------------------------------------
# Step 6 — Sanity
# ---------------------------------------------------------------------------

if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY-RUN: would 'systemctl is-active skyherd-galileo'"
    exit 0
fi

sleep 2
if systemctl is-active skyherd-galileo >/dev/null 2>&1; then
    echo "  [OK] skyherd-galileo.service is active"
else
    err "skyherd-galileo.service failed to start."
    err "Inspect: journalctl -u skyherd-galileo -n 50"
    exit 1
fi

cat <<EOF

=============================================================
  SkyHerd Galileo bootstrap complete.
  Watch the bus from the laptop:

    mosquitto_sub -h 192.168.137.1 -v -t 'skyherd/${RANCH_ID}/+/${EDGE_ID}'

  Expect heartbeat within ${HEARTBEAT_INTERVAL_SEC} s and the first
  water_tank.reading within ${PUBLISH_INTERVAL_SEC} s.
=============================================================
EOF
