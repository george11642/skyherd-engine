#!/usr/bin/env bash
# setup-edge-pi.sh — one-command SkyHerd Pi 4 edge bringup from a laptop.
#
# Usage:
#   bash scripts/setup-edge-pi.sh edge-house
#   bash scripts/setup-edge-pi.sh edge-barn  --phase-a-only
#   bash scripts/setup-edge-pi.sh edge-house --dry-run
#
# Sequence (plan §1):
#   Phase A — Laptop environment (broker, portproxy, wifi SSID + PSK cache)
#   Phase B — SD card flash (first physical gate + drive selection)
#   Phase C — Move SD back to Pi (second physical gate, discovery begins)
#   Phase D — Pi discovery + remote bootstrap
#   Phase E — End-to-end verification
#
# Respects:
#   SKYHERD_EDGE_SETUP_SKIP_PHASES=A,B     skip those phases (for re-runs)
#   DRY_RUN=1 (or --dry-run)               no sudo / no network writes
#   --phase-a-only                         stop cleanly after Phase A
#
# Cached secrets live in ${REPO_ROOT}/.skyherd-edge-setup.env (chmod 600,
# gitignored). The file is read at the top of Phase A and written back any
# time a new value is captured.

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"
ENV_FILE="${REPO_ROOT}/.skyherd-edge-setup.env"
FLASH_TMP="/tmp/skyherd-flash"
IMAGE_CACHE="${HOME}/.cache/skyherd-pi"
MQTT_LOG="/tmp/skyherd-mqtt.log"
MQTT_PID_FILE="/tmp/skyherd-mqtt-sub.pid"

EDGE_ID=""
PHASE_A_ONLY=0
DRY_RUN=0
SKIP_PHASES=""

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        edge-house|edge-barn)
            EDGE_ID="$arg"
            ;;
        --phase-a-only)
            PHASE_A_ONLY=1
            ;;
        --dry-run)
            DRY_RUN=1
            ;;
        --skip=*)
            SKIP_PHASES="${arg#--skip=}"
            ;;
        -h|--help)
            sed -n '2,25p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown arg: $arg" >&2
            echo "Usage: $0 <edge-house|edge-barn> [--phase-a-only] [--dry-run] [--skip=A,B]" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$EDGE_ID" ]]; then
    echo "error: first arg must be edge-house or edge-barn" >&2
    echo "Usage: $0 <edge-house|edge-barn> [--phase-a-only] [--dry-run]" >&2
    exit 2
fi

# Env override takes precedence over CLI --skip.
if [[ -n "${SKYHERD_EDGE_SETUP_SKIP_PHASES:-}" ]]; then
    SKIP_PHASES="${SKYHERD_EDGE_SETUP_SKIP_PHASES}"
fi
export DRY_RUN

# Trough IDs per edge.
# edge-house is now the sole Pi edge node (covers ALL six trough cameras); the
# second telemetry node is a Galileo (see docs/HARDWARE_GALILEO.md).
# edge-barn remains accepted as a legacy split (troughs 3-6) for backward
# compatibility with the older two-Pi layout.
case "$EDGE_ID" in
    edge-house) TROUGH_IDS_JSON="[1,2,3,4,5,6]" ;;
    edge-barn)  TROUGH_IDS_JSON="[3,4,5,6]" ;;
esac

# ---------------------------------------------------------------------------
# Source libraries
# ---------------------------------------------------------------------------
# shellcheck source=lib/pi-env.sh
source "${LIB_DIR}/pi-env.sh"
# shellcheck source=lib/pi-flash.sh
source "${LIB_DIR}/pi-flash.sh"
# shellcheck source=lib/pi-discover.sh
source "${LIB_DIR}/pi-discover.sh"

# ---------------------------------------------------------------------------
# Visual helpers — ASCII so CI/logs stay clean.
# ---------------------------------------------------------------------------
_banner()   { printf '\n=============================================================\n  %s\n=============================================================\n' "$*"; }
_ok()       { printf '  [OK]    %s\n' "$*"; }
_fail()     { printf '  [FAIL]  %s\n' "$*" >&2; }
_warn()     { printf '  [WARN]  %s\n' "$*" >&2; }
_info()     { printf '  [..]    %s\n' "$*"; }
_step()     { printf '\n--- %s ---\n' "$*"; }

should_skip_phase() {
    local ph="$1"
    [[ ",${SKIP_PHASES}," == *",${ph},"* ]]
}

# ---------------------------------------------------------------------------
# Phase A — Laptop environment
# ---------------------------------------------------------------------------
phase_a() {
    _banner "Phase A — Laptop environment (edge_id=${EDGE_ID})"

    # A.1 — Detect env
    local wsl2
    wsl2="$(detect_wsl2)"
    if [[ "$wsl2" == "yes" ]]; then
        _ok "WSL2 detected"
    else
        _info "native Linux (not WSL2) — portproxy step will be skipped"
    fi

    # A.2 — Windows host LAN IP (WSL2 only)
    local win_ip=""
    if [[ "$wsl2" == "yes" ]]; then
        if win_ip="$(windows_host_lan_ip)" && [[ -n "$win_ip" ]]; then
            _ok "Windows host LAN IP: ${win_ip}"
        else
            _warn "could not detect Windows host LAN IP (VPN or odd network?)"
            win_ip=""
        fi
    fi
    export SKYHERD_WINDOWS_LAN_IP="$win_ip"

    # A.3 — Start broker
    _step "starting MQTT broker"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        _info "DRY-RUN: would run 'make bus-up'"
    else
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^skyherd-mosquitto$'; then
            _ok "broker already running (skyherd-mosquitto)"
        elif command -v docker >/dev/null 2>&1; then
            if (cd "$REPO_ROOT" && make bus-up >/dev/null 2>&1); then
                # Give the container a second to open the port.
                sleep 2
                _ok "broker started (skyherd-mosquitto on :1883)"
            else
                _warn "make bus-up failed — broker may already be up elsewhere"
            fi
        else
            _warn "docker not available — skipping broker start (broker must already be listening on :1883)"
        fi
    fi

    # A.4 — Windows portproxy (WSL2 only)
    if [[ "$wsl2" == "yes" ]]; then
        _step "configuring Windows portproxy (WSL2 → LAN)"
        if [[ "$DRY_RUN" -eq 1 ]]; then
            setup_windows_portproxy "0.0.0.0" "1883" "127.0.0.1" "1883" || true
        else
            local rc=0
            setup_windows_portproxy "0.0.0.0" "1883" "127.0.0.1" "1883" || rc=$?
            case "$rc" in
                0) _ok "portproxy + firewall rule configured" ;;
                2) _warn "Windows UAC declined — falling back to manual instructions"
                   print_manual_portproxy_instructions "1883" "127.0.0.1" ;;
                *) _warn "portproxy setup returned rc=$rc — continuing (broker still reachable on 127.0.0.1)" ;;
            esac
        fi
    fi

    # A.5 — Wifi SSID + PSK
    _step "wifi credentials"
    # If cached env already has SSID, prefer that (user can edit the env file to override).
    local detected_ssid=""
    if [[ "$wsl2" == "yes" ]]; then
        detected_ssid="$(detect_current_wifi_ssid || true)"
    fi
    if [[ -z "${SKYHERD_WIFI_SSID:-}" ]]; then
        if [[ -n "$detected_ssid" ]]; then
            export SKYHERD_WIFI_SSID="$detected_ssid"
            _ok "detected current wifi SSID: ${SKYHERD_WIFI_SSID}"
        else
            # Prompt — can't detect (ethernet-only laptop, or netsh failed).
            echo ""
            printf "  Wi-Fi SSID the Pi should join: "
            read -r entered_ssid
            if [[ -z "$entered_ssid" ]]; then
                _fail "SSID required"
                return 1
            fi
            export SKYHERD_WIFI_SSID="$entered_ssid"
        fi
    fi

    # load_or_prompt_credentials writes ENV_FILE with chmod 600, populates
    # SKYHERD_WIFI_PSK + SKYHERD_PI_PASSWORD. Guard the return: on empty PSK
    # it returns non-zero and leaves SKYHERD_PI_PASSWORD unset.
    if ! load_or_prompt_credentials "$ENV_FILE"; then
        _fail "credentials capture failed (PSK required)"
        return 1
    fi
    # Security: never echo the PSK or Pi password. Only the SSID + a masked
    # marker go to stdout.
    local pw_len=${#SKYHERD_PI_PASSWORD}
    _ok "SSID cached; PSK captured (${#SKYHERD_WIFI_PSK} chars, hidden); Pi password generated (${pw_len} chars, hidden)"
    _info "cached to: ${ENV_FILE} (chmod 600, gitignored)"

    # A.6 — Background mosquitto_sub logger (skip in dry-run)
    _step "MQTT subscriber"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        _info "DRY-RUN: would start 'mosquitto_sub -h 127.0.0.1 -v -t skyherd/ranch_a/# > ${MQTT_LOG} &'"
    else
        if ! command -v mosquitto_sub >/dev/null 2>&1; then
            _warn "mosquitto_sub not installed — skipping live MQTT log"
            _info "install with: sudo apt-get install -y mosquitto-clients"
        elif [[ -f "$MQTT_PID_FILE" ]] && kill -0 "$(cat "$MQTT_PID_FILE")" 2>/dev/null; then
            _ok "MQTT subscriber already running (pid $(cat "$MQTT_PID_FILE"))"
        else
            # Start in background, redirecting stdout/stderr to the log.
            nohup mosquitto_sub -h 127.0.0.1 -v -t 'skyherd/ranch_a/#' \
                >"$MQTT_LOG" 2>&1 &
            echo "$!" > "$MQTT_PID_FILE"
            sleep 1
            if kill -0 "$(cat "$MQTT_PID_FILE")" 2>/dev/null; then
                _ok "MQTT subscriber started (pid $(cat "$MQTT_PID_FILE")); log: ${MQTT_LOG}"
            else
                _warn "MQTT subscriber did not start cleanly — broker may not be listening yet"
            fi
        fi
    fi

    # A.7 — Status summary
    _step "Phase A summary"
    printf '    edge_id          = %s\n' "$EDGE_ID"
    printf '    trough_ids       = %s\n' "$TROUGH_IDS_JSON"
    printf '    wsl2             = %s\n' "$wsl2"
    printf '    windows_lan_ip   = %s\n' "${SKYHERD_WINDOWS_LAN_IP:-<not-detected>}"
    printf '    wifi_ssid        = %s\n' "${SKYHERD_WIFI_SSID}"
    printf '    mqtt_url         = mqtt://%s:1883\n' "${SKYHERD_WINDOWS_LAN_IP:-<LAN-IP>}"
    printf '    env_file         = %s (chmod 600)\n' "$ENV_FILE"
    _ok "Phase A complete"
    return 0
}

# ---------------------------------------------------------------------------
# Phase B — Flash SD card
# ---------------------------------------------------------------------------
phase_b() {
    _banner "Phase B — SD card flash"

    if [[ -z "${SKYHERD_WINDOWS_LAN_IP:-}" ]]; then
        _warn "Windows LAN IP not set — Pi will get mqtt_url with placeholder. Re-run Phase A."
        return 1
    fi

    local mqtt_url="mqtt://${SKYHERD_WINDOWS_LAN_IP}:1883"

    _step "pause 1 of 2: SD card"
    echo ""
    echo "  >>> Remove the SD card from the Pi, insert into the laptop's USB SD reader."
    echo "  >>> Press ENTER when inserted."
    read -r _ignored

    # Detect removable drives.
    _step "detecting SD card"
    local drives
    drives="$(detect_removable_drives)"
    local count
    count="$(printf '%s\n' "$drives" | grep -c '^/dev/' || true)"

    local device=""
    if [[ "$count" -eq 0 ]]; then
        _fail "no removable drive found"
        _info "WSL2? Run 'usbipd list' in PowerShell and attach the SD reader's busid:"
        _info "  usbipd bind --busid <BUSID>"
        _info "  usbipd attach --wsl --busid <BUSID>"
        return 1
    elif [[ "$count" -eq 1 ]]; then
        device="$(printf '%s\n' "$drives" | awk 'NR==1 {print $1}')"
        _info "one removable drive detected:"
        printf '%s\n' "$drives" | sed 's/^/    /'
        printf "  Confirm flash target: %s [y/N]: " "$device"
        read -r confirm
        if [[ "${confirm,,}" != "y" ]]; then
            _fail "aborted by user"
            return 1
        fi
    else
        _info "multiple removable drives detected:"
        printf '%s\n' "$drives" | nl -ba | sed 's/^/    /'
        printf "  Enter the number of the SD card to flash (or 'q' to abort): "
        read -r pick
        if [[ "$pick" == "q" ]]; then
            _fail "aborted by user"
            return 1
        fi
        device="$(printf '%s\n' "$drives" | awk -v n="$pick" 'NR==n {print $1}')"
        if [[ -z "$device" ]]; then
            _fail "invalid selection"
            return 1
        fi
        printf "  Confirm flash target: %s [y/N]: " "$device"
        read -r confirm
        if [[ "${confirm,,}" != "y" ]]; then
            _fail "aborted by user"
            return 1
        fi
    fi
    _ok "target: $device"

    # Download image.
    _step "downloading RPi OS Lite 64-bit Bookworm"
    local image
    image="$(download_rpi_image "$IMAGE_CACHE")" || {
        _fail "image download/verify failed"
        return 1
    }
    _ok "image ready: $image"

    # Flash.
    _step "flashing (this takes several minutes)"
    flash_sd_card "$device" "$image" || {
        _fail "flash failed"
        return 1
    }
    _ok "flash complete"

    # Mount boot partition and inject first-boot config.
    _step "injecting first-boot config"
    local boot_mount="${FLASH_TMP}/boot"
    mkdir -p "$boot_mount"
    local boot_part="${device}1"
    # Some devices use pN naming (mmcblk0p1). Try both.
    if [[ ! -b "$boot_part" && -b "${device}p1" ]]; then
        boot_part="${device}p1"
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        _info "DRY-RUN: would mount $boot_part and inject files at $boot_mount"
    else
        sudo mount "$boot_part" "$boot_mount" || {
            _fail "could not mount boot partition ($boot_part)"
            return 1
        }
        trap "sudo umount '$boot_mount' 2>/dev/null || true" EXIT

        local _wifi_mode="${SKYHERD_WIFI_MODE:-psk}"
        if [[ "$_wifi_mode" == "eap" ]]; then
            inject_first_boot eap \
                "$boot_mount" \
                "$EDGE_ID" \
                "$TROUGH_IDS_JSON" \
                "${SKYHERD_WIFI_SSID}" \
                "${SKYHERD_WIFI_EAP_IDENTITY}" \
                "${SKYHERD_WIFI_EAP_PASSWORD}" \
                "${SKYHERD_WIFI_EAP_PHASE2:-MSCHAPV2}" \
                "$mqtt_url" \
                "${SKYHERD_PI_PASSWORD}" \
                "${SKYHERD_WIFI_EAP_METHOD:-PEAP}" \
                "${SKYHERD_WIFI_COUNTRY:-US}" || {
                _fail "first-boot injection failed (eap)"
                sudo umount "$boot_mount" 2>/dev/null || true
                return 1
            }
        else
            inject_first_boot psk \
                "$boot_mount" \
                "$EDGE_ID" \
                "$TROUGH_IDS_JSON" \
                "${SKYHERD_WIFI_SSID}" \
                "${SKYHERD_WIFI_PSK}" \
                "$mqtt_url" \
                "${SKYHERD_PI_PASSWORD}" || {
                _fail "first-boot injection failed"
                sudo umount "$boot_mount" 2>/dev/null || true
                return 1
            }
        fi
        sync
        sudo umount "$boot_mount"
        trap - EXIT
    fi
    _ok "first-boot config written (ssh, userconf.txt, custom.toml, skyherd-credentials.json)"
    return 0
}

# ---------------------------------------------------------------------------
# Phase C — Second physical act
# ---------------------------------------------------------------------------
phase_c() {
    _banner "Phase C — move SD card back to Pi"
    echo ""
    echo "  >>> Remove SD card from laptop. Insert into Pi. Keep USB-C power connected."
    echo "  >>> Press ENTER when inserted (discovery will start automatically)."
    read -r _ignored
    return 0
}

# ---------------------------------------------------------------------------
# Phase D — Discovery + remote bootstrap
# ---------------------------------------------------------------------------
phase_d() {
    _banner "Phase D — Pi discovery + remote bootstrap"

    _step "waiting for ${EDGE_ID}.local on LAN (up to 5 min)"
    local pi_ip
    if ! pi_ip="$(discover_pi "$EDGE_ID" 300)"; then
        _fail "Pi not found within 5 min"
        _info "Verify: (a) Pi has power, (b) SD card is seated, (c) wifi SSID/PSK in env match a nearby AP."
        return 1
    fi
    _ok "Pi is at ${pi_ip}"
    export SKYHERD_PI_IP="$pi_ip"

    # SSH in and run bootstrap. sshpass is preferred; fall back to manual.
    _step "remote bootstrap over SSH"
    if ! command -v sshpass >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then
            _info "installing sshpass..."
            sudo apt-get update -qq >/dev/null 2>&1 || true
            sudo apt-get install -y sshpass >/dev/null 2>&1 || true
        fi
    fi
    if ! command -v sshpass >/dev/null 2>&1; then
        _warn "sshpass unavailable — manual step:"
        cat <<EOF
    ssh pi@${pi_ip}
    (password: see ${ENV_FILE})
    curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash
EOF
        return 1
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        _info "DRY-RUN: would sshpass-ssh pi@${pi_ip} and run bootstrap.sh"
        return 0
    fi

    SSHPASS="${SKYHERD_PI_PASSWORD}" sshpass -e ssh \
        -o StrictHostKeyChecking=accept-new \
        -o UserKnownHostsFile=/dev/null \
        "pi@${pi_ip}" \
        "curl -sSfL https://raw.githubusercontent.com/george11642/skyherd-engine/main/hardware/pi/bootstrap.sh | bash" \
        || {
            _fail "remote bootstrap failed"
            return 1
        }

    # Post-boot sanity: undervoltage check.
    local throttled=""
    throttled="$(SSHPASS="${SKYHERD_PI_PASSWORD}" sshpass -e ssh \
        -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null \
        "pi@${pi_ip}" "vcgencmd get_throttled" 2>/dev/null || true)"
    if [[ -n "$throttled" && "$throttled" != "throttled=0x0" ]]; then
        _warn "undervoltage or thermal event detected on Pi: ${throttled}"
        _warn "the setup still completed — swap to an official 5V/3A PSU before demo."
    elif [[ -n "$throttled" ]]; then
        _ok "Pi voltage stable (${throttled})"
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Phase E — End-to-end verify
# ---------------------------------------------------------------------------
phase_e() {
    _banner "Phase E — verify end-to-end"

    # E.1 — tail mosquitto log for edge_status from this edge.
    _step "waiting for heartbeat on skyherd/ranch_a/edge_status/${EDGE_ID}"
    if [[ ! -f "$MQTT_LOG" ]]; then
        _warn "MQTT log missing (${MQTT_LOG}) — Phase A may not have run"
        return 1
    fi
    local deadline=$(( $(date +%s) + 120 ))
    local found=0
    while [[ $(date +%s) -lt $deadline ]]; do
        if grep -q "edge_status/${EDGE_ID}" "$MQTT_LOG" 2>/dev/null; then
            found=1
            break
        fi
        sleep 2
    done
    if [[ "$found" -eq 1 ]]; then
        _ok "heartbeat observed on bus"
    else
        _warn "no heartbeat observed in 120 s"
    fi

    # E.2 — systemctl check over SSH (optional — already logged during bootstrap)
    if [[ -n "${SKYHERD_PI_IP:-}" ]] && command -v sshpass >/dev/null 2>&1; then
        local active
        active="$(SSHPASS="${SKYHERD_PI_PASSWORD}" sshpass -e ssh \
            -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null \
            "pi@${SKYHERD_PI_IP}" 'systemctl is-active skyherd-edge' 2>/dev/null || true)"
        if [[ "$active" == "active" ]]; then
            _ok "skyherd-edge.service is active on the Pi"
        else
            _warn "skyherd-edge.service state: ${active:-unknown}"
        fi
    fi

    _banner "DONE — ${EDGE_ID} is demo-ready"
    cat <<EOF
  Pi IP:           ${SKYHERD_PI_IP:-<unknown>}
  Edge ID:         ${EDGE_ID}
  Watch live:      mosquitto_sub -h 127.0.0.1 -v -t 'skyherd/ranch_a/#'
  MQTT log:        ${MQTT_LOG}
  SSH:             ssh pi@${SKYHERD_PI_IP:-<ip>}    (password in ${ENV_FILE})

EOF
    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    local rc=0

    if ! should_skip_phase A; then
        phase_a || rc=$?
    else
        _info "Phase A skipped (SKYHERD_EDGE_SETUP_SKIP_PHASES)"
    fi

    if [[ "$PHASE_A_ONLY" -eq 1 ]]; then
        _banner "--phase-a-only: stopping cleanly"
        exit "$rc"
    fi

    if [[ "$rc" -ne 0 ]]; then
        _fail "Phase A did not complete cleanly — aborting before flashing"
        exit "$rc"
    fi

    if ! should_skip_phase B; then
        phase_b || { _fail "Phase B failed"; exit 1; }
    fi
    if ! should_skip_phase C; then
        phase_c || { _fail "Phase C failed"; exit 1; }
    fi
    if ! should_skip_phase D; then
        phase_d || { _fail "Phase D failed"; exit 1; }
    fi
    if ! should_skip_phase E; then
        phase_e || { _warn "Phase E had soft failures — inspect logs"; }
    fi
}

main "$@"
