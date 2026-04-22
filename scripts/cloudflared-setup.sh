#!/usr/bin/env bash
# cloudflared-setup.sh — expose local SkyHerd webhook endpoint via Cloudflare Tunnel
#
# Usage:
#   ./scripts/cloudflared-setup.sh [LOCAL_PORT]
#
# This script:
#   1. Checks that cloudflared is installed (installs if missing on Debian/Ubuntu).
#   2. Starts a quick tunnel to the local FastAPI server.
#   3. Prints the public HTTPS URL to use as the Managed Agents webhook destination.
#
# Environment variables:
#   LOCAL_PORT          — local port FastAPI is listening on (default: 8000)
#   CLOUDFLARED_TOKEN   — if set, runs a named tunnel instead of a quick tunnel
#
# Prerequisites:
#   - cloudflared >= 2024.x  (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
#   - SkyHerd FastAPI server already running on LOCAL_PORT
#   - SKYHERD_WEBHOOK_SECRET set in your environment

set -euo pipefail

LOCAL_PORT="${1:-${LOCAL_PORT:-8000}}"
WEBHOOK_PATH="/webhooks/managed-agents"

# ---------------------------------------------------------------------------
# 1. Ensure cloudflared is available
# ---------------------------------------------------------------------------
if ! command -v cloudflared &>/dev/null; then
    echo "[cloudflared-setup] cloudflared not found. Attempting install..."
    if command -v apt-get &>/dev/null; then
        curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
            | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
        echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" \
            | sudo tee /etc/apt/sources.list.d/cloudflared.list
        sudo apt-get update -q && sudo apt-get install -y cloudflared
    else
        echo "[cloudflared-setup] ERROR: cannot auto-install cloudflared on this OS."
        echo "  → Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi
fi

CLOUDFLARED_VERSION="$(cloudflared version 2>&1 | head -1)"
echo "[cloudflared-setup] Using: ${CLOUDFLARED_VERSION}"

# ---------------------------------------------------------------------------
# 2. Warn if SKYHERD_WEBHOOK_SECRET is not set
# ---------------------------------------------------------------------------
if [[ -z "${SKYHERD_WEBHOOK_SECRET:-}" ]]; then
    echo "[cloudflared-setup] WARNING: SKYHERD_WEBHOOK_SECRET is not set."
    echo "  Webhook signature verification is disabled — set this in .env.local for production."
fi

# ---------------------------------------------------------------------------
# 3. Start tunnel
# ---------------------------------------------------------------------------
if [[ -n "${CLOUDFLARED_TOKEN:-}" ]]; then
    echo "[cloudflared-setup] Starting named tunnel with provided token..."
    exec cloudflared tunnel run --token "${CLOUDFLARED_TOKEN}"
else
    echo "[cloudflared-setup] Starting quick tunnel → http://localhost:${LOCAL_PORT}"
    echo "[cloudflared-setup] Webhook endpoint will be: <tunnel-url>${WEBHOOK_PATH}"
    echo "[cloudflared-setup] Set this URL in the Managed Agents dashboard as the webhook destination."
    echo ""
    exec cloudflared tunnel --url "http://localhost:${LOCAL_PORT}"
fi
