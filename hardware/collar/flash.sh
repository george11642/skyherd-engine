#!/usr/bin/env bash
# flash.sh — one-shot flash wrapper for the SkyHerd LoRa GPS collar.
#
# Usage:
#   ./hardware/collar/flash.sh                    # flash default env (rak3172)
#   ./hardware/collar/flash.sh --env heltec       # flash the ESP32 alt env
#   ./hardware/collar/flash.sh --monitor          # tail the serial monitor for 20s
#   ./hardware/collar/flash.sh --no-warn          # skip the BOOT0 prompt
#   ./hardware/collar/flash.sh --help             # show this help and exit
#
# Exit codes:
#   0  success
#   2  pre-flight tool missing (PlatformIO not on PATH)
#   3  flash failed

set -euo pipefail

ENV_NAME="rak3172"
MONITOR=0
WARN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIRMWARE_DIR="${SCRIPT_DIR}/firmware"
SECRETS_PATH="${FIRMWARE_DIR}/include/secrets.h"
SECRETS_EXAMPLE="${FIRMWARE_DIR}/include/secrets.h.example"

usage() {
    cat <<'USAGE'
SkyHerd collar flash script

Usage:
  flash.sh [options]

Options:
  --env <name>     PlatformIO env to build+flash (default: rak3172)
                   choices: rak3172 | heltec
  --monitor        After flash, tail `pio device monitor` for 20s.
  --no-warn        Skip the interactive BOOT0/RESET prompt.
  --help           Print this help and exit 0.

Exit codes:
  0 success
  2 missing PlatformIO CLI
  3 flash failed

Before running for the first time, copy secrets.h.example to secrets.h and
fill in your DEV_EUI / APP_EUI / APP_KEY from the ChirpStack device page.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            ENV_NAME="${2:-}"
            shift 2
            ;;
        --monitor)
            MONITOR=1
            shift
            ;;
        --no-warn)
            WARN=0
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown arg: $1" >&2
            usage >&2
            exit 64
            ;;
    esac
done

# --- pre-flight: PlatformIO --------------------------------------------------
if ! command -v pio >/dev/null 2>&1; then
    cat >&2 <<'MSG'
ERROR: `pio` (PlatformIO Core) is not on PATH.

Install with:
    pip install --user platformio

Then re-run this script. See docs/HARDWARE_H4_RUNBOOK.md for details.
MSG
    exit 2
fi

# --- pre-flight: secrets.h ---------------------------------------------------
if [[ ! -f "${SECRETS_PATH}" ]]; then
    if [[ -f "${SECRETS_EXAMPLE}" ]]; then
        cp "${SECRETS_EXAMPLE}" "${SECRETS_PATH}"
        echo "Created ${SECRETS_PATH} from example — EDIT IT NOW with real DevEUI/AppEUI/AppKey"
        echo "Then re-run this script."
        exit 2
    else
        echo "ERROR: neither ${SECRETS_PATH} nor ${SECRETS_EXAMPLE} exists." >&2
        exit 2
    fi
fi

# --- interactive warn --------------------------------------------------------
if [[ "${WARN}" == "1" ]]; then
    cat <<'PROMPT'
─────────────────────────────────────────────────────────────
Before continuing, put the collar MCU into DFU bootloader mode:
  1. Hold BOOT0 pin
  2. Press and release RESET
  3. Release BOOT0

Press ENTER when ready, or Ctrl+C to abort.
─────────────────────────────────────────────────────────────
PROMPT
    # shellcheck disable=SC2034
    read -r _ignored
fi

# --- flash -------------------------------------------------------------------
echo ">> pio run -e ${ENV_NAME} -t upload (from ${FIRMWARE_DIR})"
if ! (cd "${FIRMWARE_DIR}" && pio run -e "${ENV_NAME}" -t upload); then
    echo "ERROR: flash failed — check USB-C cable, DFU mode, and dmesg." >&2
    exit 3
fi

echo "✓ Flash complete."

# --- optional monitor --------------------------------------------------------
if [[ "${MONITOR}" == "1" ]]; then
    echo ">> pio device monitor (20 s)"
    (cd "${FIRMWARE_DIR}" && timeout 20s pio device monitor --baud 115200 || true)
fi

exit 0
