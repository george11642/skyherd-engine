#!/usr/bin/env bash
# bootstrap.sh — One-command SkyHerd Pi H1 bringup.
#
# Usage (on the Pi itself, or curl-piped from laptop):
#
#   curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
#
# Or manually, after cloning the repo to the Pi:
#
#   bash hardware/pi/bootstrap.sh
#
# Input: credentials.json on the Pi, default location
#          /boot/firmware/skyherd-credentials.json
#        (Raspberry Pi Imager can drop it there during the flash step.)
#        Override via env: SKYHERD_CREDS_FILE=/path/to/creds.json bash bootstrap.sh
#
# Supported flags:
#   --dry-run   Print the derived provisioning command without executing.
#
# The script:
#   1. Validates credentials.json exists + is well-formed.
#   2. Extracts wifi/mqtt/edge fields via jq.
#   3. (On a real Pi) writes wpa_supplicant.conf if wifi not yet configured.
#   4. Delegates to scripts/provision-edge.sh with the proper env.
#
# Idempotent: safe to re-run.

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SKYHERD_CREDS_FILE="${SKYHERD_CREDS_FILE:-/boot/firmware/skyherd-credentials.json}"
DRY_RUN=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,22p' "$0"
            exit 0
            ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

err() { echo "bootstrap.sh: $*" >&2; }

require_cmd() {
    if ! command -v "$1" &>/dev/null; then
        err "required command '$1' not installed — installing via apt..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq >/dev/null
            sudo apt-get install -y "$1" >/dev/null
        else
            err "apt-get not available; cannot install '$1' automatically."
            exit 2
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 1 — credentials.json
# ---------------------------------------------------------------------------

if [ ! -f "$SKYHERD_CREDS_FILE" ]; then
    err "credentials file not found: $SKYHERD_CREDS_FILE"
    err "Drop a credentials.json on /boot/firmware/ (Pi Imager advanced options),"
    err "or set SKYHERD_CREDS_FILE=/path/to/creds.json."
    exit 2
fi

# jq is only hard-required on actual Pi; in dry-run mode we still use it but it
# should already be present on dev machines.
if [ "$DRY_RUN" -eq 0 ]; then
    require_cmd jq
else
    if ! command -v jq &>/dev/null; then
        err "dry-run: jq required for parsing but not installed."
        exit 2
    fi
fi

# Validate JSON
if ! jq . "$SKYHERD_CREDS_FILE" >/dev/null 2>&1; then
    err "credentials file is not valid JSON: $SKYHERD_CREDS_FILE"
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 2 — Extract fields
# ---------------------------------------------------------------------------

# Required fields
WIFI_SSID=$(jq -r '.wifi_ssid // empty' "$SKYHERD_CREDS_FILE")
WIFI_PSK=$(jq -r '.wifi_psk  // empty' "$SKYHERD_CREDS_FILE")
MQTT_URL=$(jq -r '.mqtt_url  // empty' "$SKYHERD_CREDS_FILE")
RANCH_ID=$(jq -r '.ranch_id  // empty' "$SKYHERD_CREDS_FILE")
EDGE_ID=$(jq -r '.edge_id    // empty' "$SKYHERD_CREDS_FILE")
TROUGH_IDS=$(jq -r '.trough_ids // empty' "$SKYHERD_CREDS_FILE")

MISSING=""
[ -z "$WIFI_SSID"  ] && MISSING="$MISSING wifi_ssid"
[ -z "$WIFI_PSK"   ] && MISSING="$MISSING wifi_psk"
[ -z "$MQTT_URL"   ] && MISSING="$MISSING mqtt_url"
[ -z "$RANCH_ID"   ] && MISSING="$MISSING ranch_id"
[ -z "$EDGE_ID"    ] && MISSING="$MISSING edge_id"
[ -z "$TROUGH_IDS" ] && MISSING="$MISSING trough_ids"

if [ -n "$MISSING" ]; then
    err "missing required field(s):$MISSING"
    err "see hardware/pi/credentials.example.json for the full schema."
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 3 — Derive provisioning command
# ---------------------------------------------------------------------------

# Locate the repo root (containing scripts/provision-edge.sh).
# If running from inside a checkout, PWD is the repo root; otherwise fall back
# to /opt/skyherd-engine which is where provision-edge.sh itself clones to.
if [ -f "scripts/provision-edge.sh" ]; then
    REPO_ROOT="$(pwd)"
elif [ -f "/opt/skyherd-engine/scripts/provision-edge.sh" ]; then
    REPO_ROOT="/opt/skyherd-engine"
else
    # Dry-run: tolerate absence so the test harness works from anywhere.
    REPO_ROOT="${REPO_ROOT:-/opt/skyherd-engine}"
fi

PROVISION_CMD=(env
    "RANCH_ID=$RANCH_ID"
    "MQTT_URL=$MQTT_URL"
    "bash" "$REPO_ROOT/scripts/provision-edge.sh"
    "$EDGE_ID" "$TROUGH_IDS"
)

echo "============================================================"
echo " SkyHerd Pi Bootstrap"
echo " edge_id    = $EDGE_ID"
echo " ranch_id   = $RANCH_ID"
echo " mqtt_url   = $MQTT_URL"
echo " trough_ids = $TROUGH_IDS"
echo " repo_root  = $REPO_ROOT"
echo "============================================================"

# ---------------------------------------------------------------------------
# Step 4 — Dry-run or execute
# ---------------------------------------------------------------------------

if [ "$DRY_RUN" -eq 1 ]; then
    printf 'DRY-RUN: '
    printf '%q ' "${PROVISION_CMD[@]}"
    echo
    echo "DRY-RUN: would provision edge node '$EDGE_ID' with troughs '$TROUGH_IDS'."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 5 — (Real Pi only) wifi, if not already online
# ---------------------------------------------------------------------------

# If we can't reach the MQTT host already, try to bring up wifi.
# This is a best-effort nicety; most Pi deployments have wifi pre-configured
# via the Imager's advanced options so this step is usually a no-op.

if ! ip route | grep -q default && [ -w /etc/wpa_supplicant ]; then
    echo "No default route — writing /etc/wpa_supplicant/wpa_supplicant.conf"
    WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
    sudo tee "$WPA_CONF" > /dev/null <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$WIFI_SSID"
    psk="$WIFI_PSK"
    key_mgmt=WPA-PSK
}
EOF
    sudo chmod 600 "$WPA_CONF"
    sudo rfkill unblock wifi 2>/dev/null || true
    sudo wpa_cli -i wlan0 reconfigure 2>/dev/null || true
    echo "Waiting up to 30s for wifi..."
    for _ in {1..30}; do
        if ip route | grep -q default; then break; fi
        sleep 1
    done
fi

# ---------------------------------------------------------------------------
# Step 6 — Delegate to provision-edge.sh
# ---------------------------------------------------------------------------

if [ ! -f "$REPO_ROOT/scripts/provision-edge.sh" ]; then
    err "provision-edge.sh not found at $REPO_ROOT/scripts/"
    err "Clone skyherd-engine to $REPO_ROOT first, or set REPO_ROOT env."
    exit 2
fi

echo ""
echo "Delegating to: ${PROVISION_CMD[*]}"
echo ""
exec "${PROVISION_CMD[@]}"
