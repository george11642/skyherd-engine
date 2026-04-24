#!/usr/bin/env bash
# pi-flash.sh — SD card detection, image download, flash, and first-boot
# config injection for the one-command Pi bringup.
#
# Sourced by scripts/setup-edge-pi.sh. Every destructive op honours $DRY_RUN.
#
# NB: the flash itself runs `sudo dd` + mount, which cannot be dry-run-ed
# without mocking at a higher level. The unit tests in tests/hardware/
# test_pi_flash_lib.bats cover the pure functions (drive detection, TOML
# injection) and skip the sudo paths.

# Do NOT `set -euo pipefail` here — sourced file.

# Upstream Raspberry Pi OS Lite 64-bit Bookworm. Pinned image date so
# the SHA256 stays stable across runs; bump this pair together on refresh.
: "${RPI_OS_URL:=https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-07-04/2024-07-04-raspios-bookworm-arm64-lite.img.xz}"
: "${RPI_OS_SHA_URL:=https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-07-04/2024-07-04-raspios-bookworm-arm64-lite.img.xz.sha256}"

# Raspberry Pi OUI prefixes (MAC address vendor prefixes for Pi boards).
# Used by pi-discover.sh too — exported as an array-friendly string.
RPI_OUI_PREFIXES="b8:27:eb dc:a6:32 e4:5f:01 28:cd:c1 d8:3a:dd 2c:cf:67"

# ---------------------------------------------------------------------------
# detect_removable_drives — list removable block devices, one per line,
# format: "/dev/<name> <size> <model>".
#
# We honour $LSBLK_BIN (defaults to lsblk) so tests can inject a mock.
# Filters RM=1 and TYPE=disk (excludes partitions like sdb1).
# ---------------------------------------------------------------------------
detect_removable_drives() {
    local lsblk_bin="${LSBLK_BIN:-lsblk}"
    # NAME SIZE TYPE TRAN RM MODEL — json form avoids locale surprises.
    "$lsblk_bin" -ndo NAME,SIZE,TYPE,RM,MODEL 2>/dev/null \
        | awk '$3 == "disk" && $4 == "1" {
            name=$1; size=$2;
            model=""; for (i=5; i<=NF; i++) { model = (model=="" ? $i : model" "$i) }
            printf "/dev/%s %s %s\n", name, size, (model == "" ? "unknown" : model)
        }'
}

# ---------------------------------------------------------------------------
# download_rpi_image — resume-capable download of RPi OS Lite + SHA256 verify.
#
# Usage: download_rpi_image <cache_dir>
# Echoes the absolute path to the verified .img.xz file on stdout.
# Returns 0 on success, 1 on download or verify failure.
# ---------------------------------------------------------------------------
download_rpi_image() {
    local cache_dir="$1"
    if [[ -z "$cache_dir" ]]; then
        echo "download_rpi_image: cache_dir required" >&2
        return 1
    fi
    mkdir -p "$cache_dir"

    local image_name
    image_name="$(basename "$RPI_OS_URL")"
    local image_path="${cache_dir}/${image_name}"
    local sha_name="${image_name}.sha256"
    local sha_path="${cache_dir}/${sha_name}"

    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        echo "DRY-RUN: would download $RPI_OS_URL → $image_path" >&2
        echo "$image_path"
        return 0
    fi

    # Fetch sha256 (small — re-fetch each run; upstream is CDN-cached).
    if ! curl -fsSL --retry 3 --retry-delay 5 -o "$sha_path" "$RPI_OS_SHA_URL"; then
        echo "download_rpi_image: failed to fetch SHA256 sidecar" >&2
        return 1
    fi

    # If cached image already passes SHA256, skip download.
    if [[ -f "$image_path" ]] && verify_image_sha256 "$image_path" "$sha_path"; then
        echo "$image_path"
        return 0
    fi

    # Download with resume support (-C -).
    echo "download_rpi_image: fetching $image_name (~500 MB, resumable)..." >&2
    if ! curl -fL --retry 3 --retry-delay 5 -C - -o "$image_path" "$RPI_OS_URL"; then
        echo "download_rpi_image: download failed" >&2
        return 1
    fi

    if ! verify_image_sha256 "$image_path" "$sha_path"; then
        echo "download_rpi_image: SHA256 mismatch after download — refusing to use" >&2
        rm -f "$image_path"
        return 1
    fi
    echo "$image_path"
}

# ---------------------------------------------------------------------------
# verify_image_sha256 — compare sha256sum of <image> against <sha_file>.
# The sha_file format is "<hash>  <filename>" (RPi standard).
# Returns 0 iff hashes match.
# ---------------------------------------------------------------------------
verify_image_sha256() {
    local image="$1"
    local sha_file="$2"
    [[ -f "$image" && -f "$sha_file" ]] || return 1
    local expected actual
    expected="$(awk 'NR==1 {print $1}' "$sha_file")"
    actual="$(sha256sum "$image" | awk '{print $1}')"
    [[ -n "$expected" && "$expected" == "$actual" ]]
}

# ---------------------------------------------------------------------------
# flash_sd_card — xzcat | sudo dd onto the target device.
#
# Usage: flash_sd_card /dev/sdX /path/to/image.img.xz
# Caller MUST have already confirmed /dev/sdX with the user.
# ---------------------------------------------------------------------------
flash_sd_card() {
    local device="$1"
    local image="$2"
    if [[ -z "$device" || -z "$image" ]]; then
        echo "flash_sd_card: device and image required" >&2
        return 1
    fi
    if [[ ! -b "$device" && "${DRY_RUN:-0}" -ne 1 ]]; then
        echo "flash_sd_card: $device is not a block device" >&2
        return 1
    fi
    if [[ ! -f "$image" && "${DRY_RUN:-0}" -ne 1 ]]; then
        echo "flash_sd_card: image not found: $image" >&2
        return 1
    fi

    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        echo "DRY-RUN: xzcat $image | sudo dd of=$device bs=4M status=progress conv=fsync"
        return 0
    fi

    # Make absolutely sure nothing is mounted — umount best-effort.
    # Partition nodes are e.g. /dev/sdX1 or /dev/mmcblk0p1.
    local part
    for part in "${device}"* ; do
        if mountpoint -q "$part" 2>/dev/null; then
            sudo umount "$part" 2>/dev/null || true
        fi
    done

    echo "flash_sd_card: writing $image → $device (requires sudo)..."
    # shellcheck disable=SC2024
    xzcat "$image" | sudo dd of="$device" bs=4M status=progress conv=fsync
    sync
    # Re-read partition table so new partitions show up.
    sudo partprobe "$device" 2>/dev/null || true
    sleep 2
    return 0
}

# ---------------------------------------------------------------------------
# hash_pi_password — openssl passwd -6 wrapper. SHA-512 crypt, 16-char salt.
# Callers pass the plaintext and get the hash on stdout.
# ---------------------------------------------------------------------------
hash_pi_password() {
    local plaintext="$1"
    if ! command -v openssl >/dev/null 2>&1; then
        echo "hash_pi_password: openssl required" >&2
        return 1
    fi
    printf '%s' "$plaintext" | openssl passwd -6 -stdin
}

# ---------------------------------------------------------------------------
# inject_first_boot — populate the boot partition with:
#   - `ssh`             (empty file, enables sshd on first boot)
#   - `userconf.txt`    ("pi:<crypt-hash>")
#   - `custom.toml`     (Bookworm first-boot: hostname/user/wifi/ssh)
#   - `skyherd-credentials.json` (our bootstrap reads this)
#
# Usage: inject_first_boot \
#          <boot_mount> <edge_id> <trough_ids_json_array> \
#          <ssid> <psk> <mqtt_url> <pi_password_plain>
#
# Returns 0 on success; the mount must be writable.
# ---------------------------------------------------------------------------
inject_first_boot() {
    local boot_mount="$1"
    local edge_id="$2"
    local trough_ids_json="$3"   # e.g. "[1,2]" or "[3,4,5,6]"
    local ssid="$4"
    local psk="$5"
    local mqtt_url="$6"
    local pi_password_plain="$7"

    if [[ -z "$boot_mount" || -z "$edge_id" || -z "$trough_ids_json" ]]; then
        echo "inject_first_boot: missing required args" >&2
        return 1
    fi
    if [[ ! -d "$boot_mount" ]]; then
        echo "inject_first_boot: boot mount not a directory: $boot_mount" >&2
        return 1
    fi

    local pw_hash
    pw_hash="$(hash_pi_password "$pi_password_plain")" || return 1

    # 1. Empty ssh marker
    : > "${boot_mount}/ssh"

    # 2. userconf.txt (pi:hash) — crypt hash has no shell metas, safe to print.
    printf 'pi:%s\n' "$pw_hash" > "${boot_mount}/userconf.txt"

    # 3. custom.toml — must escape " in SSID/PSK for TOML. We use printf
    #    with a helper that substitutes backslashes and quotes.
    local ssid_esc psk_esc
    ssid_esc="$(_toml_escape "$ssid")"
    psk_esc="$(_toml_escape "$psk")"
    local pw_esc
    pw_esc="$(_toml_escape "$pw_hash")"

    cat > "${boot_mount}/custom.toml" <<TOML_EOF
# Raspberry Pi OS Bookworm first-boot config (generated by SkyHerd setup-edge-pi.sh).
config_version = 1

[system]
hostname = "${edge_id}"

[user]
name = "pi"
password = "${pw_esc}"
password_encrypted = true

[wlan]
ssid = "${ssid_esc}"
password = "${psk_esc}"
password_encrypted = false
hidden = false
country = "US"

[ssh]
enabled = true
password_authentication = true
TOML_EOF

    # 4. skyherd-credentials.json — JSON, so escape differently. Use jq if
    #    available, fallback to a paranoid printf.
    local creds_path="${boot_mount}/skyherd-credentials.json"
    if command -v jq >/dev/null 2>&1; then
        jq -n \
            --arg ssid "$ssid" \
            --arg psk "$psk" \
            --arg mqtt "$mqtt_url" \
            --arg edge "$edge_id" \
            --argjson troughs "$trough_ids_json" \
            '{wifi_ssid:$ssid, wifi_psk:$psk, mqtt_url:$mqtt, ranch_id:"ranch_a", edge_id:$edge, trough_ids:$troughs}' \
            > "$creds_path"
    else
        # Fallback: produce JSON by hand. _json_escape handles quotes/backslashes.
        local ssid_j psk_j mqtt_j edge_j
        ssid_j="$(_json_escape "$ssid")"
        psk_j="$(_json_escape "$psk")"
        mqtt_j="$(_json_escape "$mqtt_url")"
        edge_j="$(_json_escape "$edge_id")"
        cat > "$creds_path" <<JSON_EOF
{
  "wifi_ssid": "${ssid_j}",
  "wifi_psk": "${psk_j}",
  "mqtt_url": "${mqtt_j}",
  "ranch_id": "ranch_a",
  "edge_id": "${edge_j}",
  "trough_ids": ${trough_ids_json}
}
JSON_EOF
    fi
    chmod 600 "$creds_path" || true
    chmod 600 "${boot_mount}/userconf.txt" || true
    chmod 600 "${boot_mount}/custom.toml" || true
    return 0
}

# Internal helper — escape TOML double-quoted string. Handles backslash and ".
_toml_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    printf '%s' "$s"
}

# Internal helper — escape JSON string. Handles backslash, quote, control chars.
_json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

# ---------------------------------------------------------------------------
# usbipd_attach — WSL2 helper: attach a Windows-side USB busid into WSL2.
# No-op (return 0) on native Linux. Requires powershell.exe + usbipd-win.
#
# Usage: usbipd_attach <busid>   (e.g. "2-3")
# ---------------------------------------------------------------------------
usbipd_attach() {
    local busid="$1"
    if ! grep -qi microsoft /proc/version 2>/dev/null; then
        return 0  # not WSL2
    fi
    if [[ -z "$busid" ]]; then
        echo "usbipd_attach: busid required" >&2
        return 1
    fi
    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        echo "DRY-RUN: usbipd attach --busid $busid --wsl"
        return 0
    fi
    if ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi
    powershell.exe -NoProfile -Command "usbipd bind --busid ${busid}" </dev/null 2>/dev/null || true
    powershell.exe -NoProfile -Command "usbipd attach --wsl --busid ${busid}" </dev/null 2>/dev/null
}

# ---------------------------------------------------------------------------
# usbipd_detach — counterpart to usbipd_attach.
# ---------------------------------------------------------------------------
usbipd_detach() {
    local busid="$1"
    if ! grep -qi microsoft /proc/version 2>/dev/null; then
        return 0
    fi
    [[ -z "$busid" ]] && return 0
    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        echo "DRY-RUN: usbipd detach --busid $busid"
        return 0
    fi
    if ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi
    powershell.exe -NoProfile -Command "usbipd detach --busid ${busid}" </dev/null 2>/dev/null
}
