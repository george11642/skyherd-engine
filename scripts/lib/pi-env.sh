#!/usr/bin/env bash
# pi-env.sh — Environment detection + Windows-side helpers for setup-edge-pi.sh.
#
# Sourced by scripts/setup-edge-pi.sh. Every function is pure-shell, no globals
# set (callers read stdout). Safe to source multiple times.
#
# WSL2 specifics: the user's day-to-day setup is WSL2 Ubuntu on Windows 11.
# For MQTT to be reachable from the Pi (which lives on the physical LAN),
# Windows must portproxy 1883 → WSL2's loopback. Detecting the host LAN IP
# and driving netsh is the job of the functions below.

# Do NOT `set -euo pipefail` here — this file is sourced.

# ---------------------------------------------------------------------------
# detect_wsl2 — echo "yes" if running under WSL2, "no" otherwise.
# Returns 0 always.
# ---------------------------------------------------------------------------
detect_wsl2() {
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "yes"
    else
        echo "no"
    fi
}

# ---------------------------------------------------------------------------
# windows_host_lan_ip — print the laptop's LAN IPv4 address from Windows side.
# Filters out link-local (169.254.x.x), APIPA, loopback, and VPN tunnels
# (WireGuard, OpenVPN). Returns first match or empty string.
# ---------------------------------------------------------------------------
windows_host_lan_ip() {
    if ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi
    # Get-NetIPAddress AddressFamily IPv4, PrefixOrigin Dhcp or Manual
    # (excludes link-local/APIPA), InterfaceAlias not matching loopback/VPN.
    local ps_cmd='(Get-NetIPAddress -AddressFamily IPv4 | '
    ps_cmd+='Where-Object { $_.PrefixOrigin -in "Dhcp","Manual" -and '
    ps_cmd+='$_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL|VPN|TAP|Tailscale|WireGuard" -and '
    ps_cmd+='$_.IPAddress -notmatch "^(169\.254\.|127\.)" } | '
    ps_cmd+='Select-Object -First 1 -ExpandProperty IPAddress)'
    local ip
    ip="$(powershell.exe -NoProfile -Command "$ps_cmd" </dev/null 2>/dev/null | tr -d '\r\n ')"
    # Fallback: if filter returned nothing, loosen to any Wi-Fi or Ethernet adapter.
    if [[ -z "$ip" ]]; then
        ps_cmd='(Get-NetIPAddress -AddressFamily IPv4 | '
        ps_cmd+='Where-Object { $_.InterfaceAlias -match "Wi-Fi|Ethernet" -and '
        ps_cmd+='$_.IPAddress -notmatch "^(169\.254\.|127\.)" } | '
        ps_cmd+='Select-Object -First 1 -ExpandProperty IPAddress)'
        ip="$(powershell.exe -NoProfile -Command "$ps_cmd" </dev/null 2>/dev/null | tr -d '\r\n ')"
    fi
    if [[ -n "$ip" ]]; then
        echo "$ip"
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# detect_current_wifi_ssid — print the SSID the laptop (Windows side) is on.
# Empty string + return 1 if not on wifi (e.g. ethernet-only).
# ---------------------------------------------------------------------------
detect_current_wifi_ssid() {
    if ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi
    # netsh wlan show interfaces — parse "SSID" line (not "BSSID").
    # Output is CRLF, use tr to normalize.
    local ssid
    ssid="$(powershell.exe -NoProfile -Command 'netsh wlan show interfaces' </dev/null 2>/dev/null \
        | tr -d '\r' \
        | awk -F': ' '/^[[:space:]]+SSID[[:space:]]*:/ && !/BSSID/ {sub(/^[[:space:]]+/, "", $2); print $2; exit}')"
    if [[ -n "$ssid" ]]; then
        echo "$ssid"
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# load_or_prompt_credentials — cached wifi PSK + Pi password. Cache file is
# chmod 600, gitignored. Never echoed to stdout.
#
# Usage: load_or_prompt_credentials <env_file>
# On success, exports: SKYHERD_WIFI_PSK, SKYHERD_PI_PASSWORD,
#                      SKYHERD_WIFI_SSID (if cached).
# ---------------------------------------------------------------------------
load_or_prompt_credentials() {
    local env_file="$1"
    local existing_psk="" existing_pw="" existing_ssid=""

    if [[ -f "$env_file" ]]; then
        # shellcheck disable=SC1090
        # Source in a restricted scope — only accept known keys.
        while IFS='=' read -r key val; do
            case "$key" in
                SKYHERD_WIFI_PSK)     existing_psk="${val#\"}"; existing_psk="${existing_psk%\"}" ;;
                SKYHERD_PI_PASSWORD)  existing_pw="${val#\"}"; existing_pw="${existing_pw%\"}" ;;
                SKYHERD_WIFI_SSID)    existing_ssid="${val#\"}"; existing_ssid="${existing_ssid%\"}" ;;
            esac
        done < "$env_file"
    fi

    if [[ -n "$existing_psk" ]]; then
        export SKYHERD_WIFI_PSK="$existing_psk"
    else
        # Prompt (silent — -s hides input so PSK never echoes to terminal/log).
        echo ""
        echo "Wi-Fi PSK for SSID '${SKYHERD_WIFI_SSID:-<unknown>}':"
        echo "  (input hidden; cached to $env_file with chmod 600 for re-runs)"
        printf "  PSK: "
        read -rs entered_psk
        echo ""
        if [[ -z "$entered_psk" ]]; then
            echo "  PSK cannot be empty." >&2
            return 1
        fi
        export SKYHERD_WIFI_PSK="$entered_psk"
    fi

    if [[ -n "$existing_pw" ]]; then
        export SKYHERD_PI_PASSWORD="$existing_pw"
    else
        # Generate a random Pi password (24 hex chars = 96 bits entropy).
        local generated
        generated="$(LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 24 || true)"
        if [[ -z "$generated" ]]; then
            generated="skyherd-$(date +%s)-$RANDOM"
        fi
        export SKYHERD_PI_PASSWORD="$generated"
    fi

    if [[ -n "$existing_ssid" && -z "${SKYHERD_WIFI_SSID:-}" ]]; then
        export SKYHERD_WIFI_SSID="$existing_ssid"
    fi

    # Write back (umask 077 guarantees chmod 600).
    local tmp
    tmp="$(mktemp)"
    {
        echo "# SkyHerd Pi setup cached credentials — chmod 600, gitignored."
        echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ)."
        echo "SKYHERD_WIFI_SSID=\"${SKYHERD_WIFI_SSID:-}\""
        echo "SKYHERD_WIFI_PSK=\"${SKYHERD_WIFI_PSK}\""
        echo "SKYHERD_PI_PASSWORD=\"${SKYHERD_PI_PASSWORD}\""
    } > "$tmp"
    chmod 600 "$tmp"
    mv "$tmp" "$env_file"
    chmod 600 "$env_file" || true
    return 0
}

# ---------------------------------------------------------------------------
# setup_windows_portproxy — add netsh portproxy + firewall rule for MQTT 1883.
# Idempotent: deletes matching rules first.
#
# Usage: setup_windows_portproxy <listen_ip> <listen_port> <connect_ip> <connect_port>
# Example: setup_windows_portproxy 0.0.0.0 1883 127.0.0.1 1883
#
# Returns 0 on success, 1 if powershell.exe absent, 2 if user declined UAC.
# Soft failure if UAC declined — caller is expected to print fallback guidance.
#
# The $DRY_RUN flag (exported by caller) suppresses actual execution.
# ---------------------------------------------------------------------------
setup_windows_portproxy() {
    local listen_ip="${1:-0.0.0.0}"
    local listen_port="${2:-1883}"
    local connect_ip="${3:-127.0.0.1}"
    local connect_port="${4:-1883}"

    if ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi

    # Compose the batch of netsh commands. Using \` to escape backticks in
    # the PowerShell here-string; using `&&` replaced with `;` for sh safety.
    local script
    script=$(cat <<PS_EOF
\$ErrorActionPreference = 'SilentlyContinue';
netsh interface portproxy delete v4tov4 listenport=${listen_port} listenaddress=${listen_ip} | Out-Null;
netsh interface portproxy add    v4tov4 listenport=${listen_port} listenaddress=${listen_ip} connectport=${connect_port} connectaddress=${connect_ip};
netsh advfirewall firewall delete rule name='SkyHerd MQTT' | Out-Null;
netsh advfirewall firewall add    rule name='SkyHerd MQTT' dir=in action=allow protocol=TCP localport=${listen_port};
Write-Host 'portproxy configured';
PS_EOF
)

    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        echo "DRY-RUN: would run netsh portproxy + firewall (elevated):"
        echo "$script" | sed 's/^/  /'
        return 0
    fi

    # Start-Process -Verb RunAs pops a UAC. -Wait ensures we can collect exit.
    # The inner PowerShell runs the script; we encode to base64 to dodge
    # quoting hell. Use PowerShell's built-in EncodedCommand flag.
    local encoded
    encoded="$(printf '%s' "$script" \
        | iconv -f utf-8 -t utf-16le 2>/dev/null | base64 -w0 || true)"
    if [[ -z "$encoded" ]]; then
        return 1
    fi

    # -PassThru lets us capture the spawned process's exit code.
    local launcher
    launcher="Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList '-NoProfile','-EncodedCommand','${encoded}' | Select-Object -ExpandProperty ExitCode"
    local exit_code
    exit_code="$(powershell.exe -NoProfile -Command "$launcher" </dev/null 2>/dev/null | tr -d '\r\n ' || true)"

    if [[ "$exit_code" == "0" ]]; then
        return 0
    fi
    # UAC declined or netsh failed — return 2 so caller prints fallback.
    return 2
}

# ---------------------------------------------------------------------------
# print_manual_portproxy_instructions — shown when UAC declined.
# ---------------------------------------------------------------------------
print_manual_portproxy_instructions() {
    local listen_port="${1:-1883}"
    local connect_ip="${2:-127.0.0.1}"
    cat <<EOF

=============================================================
  Portproxy setup needs Windows admin — manual fallback
=============================================================
Open an elevated PowerShell (right-click, Run as Administrator) and paste:

  netsh interface portproxy add v4tov4 listenport=${listen_port} listenaddress=0.0.0.0 connectport=${listen_port} connectaddress=${connect_ip}
  netsh advfirewall firewall add rule name="SkyHerd MQTT" dir=in action=allow protocol=TCP localport=${listen_port}

Re-run this script with the same args — it will pick up where it left off.
=============================================================

EOF
}
