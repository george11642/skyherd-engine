#!/usr/bin/env bash
# pi-discover.sh — Pi-on-LAN discovery helpers.
#
# Two strategies, cheap-to-expensive:
#   1. mDNS  — `ping edge-house.local`. Works on most networks with avahi
#              and on macOS. Flaky on some Windows/WSL2 setups; for WSL2
#              we also try from the Windows side via powershell `Resolve-DnsName`.
#   2. OUI scan — `arp-scan --localnet`, filter for Raspberry Pi MAC prefixes.
#
# Sourced by scripts/setup-edge-pi.sh.

# Raspberry Pi OUI prefixes (lowercase, colon-separated).
# Also defined in pi-flash.sh; keep in sync.
: "${RPI_OUI_PREFIXES:=b8:27:eb dc:a6:32 e4:5f:01 28:cd:c1 d8:3a:dd 2c:cf:67}"

# ---------------------------------------------------------------------------
# discover_pi_by_hostname — ping <hostname>.local every 5s, up to <timeout>.
#
# Usage: discover_pi_by_hostname <hostname> <timeout_sec>
# Echoes the resolved IP on success, nothing on timeout. Returns 0/1.
# ---------------------------------------------------------------------------
discover_pi_by_hostname() {
    local hostname="$1"
    local timeout="${2:-300}"
    local deadline=$(( $(date +%s) + timeout ))

    while [[ $(date +%s) -lt $deadline ]]; do
        # getent works on Linux; on WSL2 mDNS can fail here but succeed via
        # powershell's Resolve-DnsName. Try both.
        local ip=""
        if command -v getent >/dev/null 2>&1; then
            ip="$(getent hosts "${hostname}.local" 2>/dev/null | awk '{print $1; exit}')"
        fi
        if [[ -z "$ip" ]] && command -v powershell.exe >/dev/null 2>&1; then
            ip="$(powershell.exe -NoProfile -Command "(Resolve-DnsName -Name ${hostname}.local -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress)" </dev/null 2>/dev/null | tr -d '\r\n ' || true)"
        fi
        if [[ -n "$ip" ]]; then
            # Sanity — try a single ping to confirm reachability.
            if ping -c 1 -W 2 "$ip" >/dev/null 2>&1; then
                echo "$ip"
                return 0
            fi
        fi
        # Also try a direct ping.local — on many networks this is faster
        # than a getent call.
        if ping -c 1 -W 2 "${hostname}.local" >/dev/null 2>&1; then
            # Parse ping's printed IP from the "from" line via a second call.
            ip="$(ping -c 1 -W 2 "${hostname}.local" 2>/dev/null \
                | awk -F'[()]' 'NR==1 {print $2; exit}')"
            if [[ -n "$ip" ]]; then
                echo "$ip"
                return 0
            fi
        fi
        sleep 5
    done
    return 1
}

# ---------------------------------------------------------------------------
# discover_pi_by_oui — arp-scan the local subnet, return first IP whose MAC
# OUI matches the Raspberry Pi prefixes.
#
# Installs arp-scan via apt if missing. On WSL2, network access to the
# physical LAN depends on WSL2 networking mode (bridged vs NAT); prints
# a warning if arp-scan finds nothing.
#
# Usage: discover_pi_by_oui <timeout_sec>
# Echoes the IP on success.
# ---------------------------------------------------------------------------
discover_pi_by_oui() {
    local timeout="${1:-300}"
    local deadline=$(( $(date +%s) + timeout ))

    if ! command -v arp-scan >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then
            echo "discover_pi_by_oui: installing arp-scan via apt..." >&2
            sudo apt-get update -qq >/dev/null 2>&1 || true
            sudo apt-get install -y arp-scan >/dev/null 2>&1 || true
        fi
        if ! command -v arp-scan >/dev/null 2>&1; then
            echo "discover_pi_by_oui: arp-scan unavailable" >&2
            return 1
        fi
    fi

    while [[ $(date +%s) -lt $deadline ]]; do
        # arp-scan needs root on most setups; fail softly if no sudo.
        local scan
        scan="$(sudo -n arp-scan --localnet --retry=1 --timeout=500 2>/dev/null || true)"
        if [[ -z "$scan" ]]; then
            scan="$(arp-scan --localnet --retry=1 --timeout=500 2>/dev/null || true)"
        fi
        if [[ -n "$scan" ]]; then
            local prefix ip
            for prefix in $RPI_OUI_PREFIXES; do
                ip="$(echo "$scan" | awk -v p="$prefix" 'tolower($2) ~ ("^"p) {print $1; exit}')"
                if [[ -n "$ip" ]]; then
                    echo "$ip"
                    return 0
                fi
            done
        fi
        sleep 10
    done
    return 1
}

# ---------------------------------------------------------------------------
# discover_pi — composite strategy.
#
# Usage: discover_pi <hostname> <timeout_sec>
# Tries hostname discovery for the first half of the window, then falls back
# to OUI scan if needed.
# ---------------------------------------------------------------------------
discover_pi() {
    local hostname="$1"
    local total_timeout="${2:-300}"
    local half=$(( total_timeout / 2 ))

    local ip
    ip="$(discover_pi_by_hostname "$hostname" "$half" 2>/dev/null || true)"
    if [[ -n "$ip" ]]; then
        echo "$ip"
        return 0
    fi
    echo "discover_pi: hostname discovery timed out, falling back to arp-scan OUI match..." >&2
    ip="$(discover_pi_by_oui "$half" 2>/dev/null || true)"
    if [[ -n "$ip" ]]; then
        echo "$ip"
        return 0
    fi
    return 1
}
