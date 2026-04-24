#!/usr/bin/env bats
# Unit tests for scripts/lib/pi-flash.sh and scripts/lib/pi-discover.sh.
#
# These tests exercise the pure-shell helpers: drive detection with a
# mocked lsblk, first-boot config injection (verified by tomllib + jq),
# and discover_pi_by_hostname's exit code paths. The destructive paths
# (`sudo dd`, real mounts) are NOT tested here — they need real hardware.
#
# Run:
#   bats tests/hardware/test_pi_flash_lib.bats

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    # shellcheck source=../../scripts/lib/pi-flash.sh
    source "${REPO_ROOT}/scripts/lib/pi-flash.sh"
    # shellcheck source=../../scripts/lib/pi-discover.sh
    source "${REPO_ROOT}/scripts/lib/pi-discover.sh"
    TESTDIR="$(mktemp -d)"
}

teardown() {
    rm -rf "$TESTDIR"
    # Clean up injected mock lsblk overrides.
    unset LSBLK_BIN
}

# ---------------------------------------------------------------------------
# detect_removable_drives — mock lsblk with 0, 1, and 2 candidates.
# ---------------------------------------------------------------------------

@test "detect_removable_drives: zero candidates" {
    cat > "$TESTDIR/lsblk" <<'MOCK'
#!/usr/bin/env bash
# Only non-removable disks and partitions.
cat <<EOF
nvme0n1 512G disk 0 Samsung SSD
sda1    100G part 0
EOF
MOCK
    chmod +x "$TESTDIR/lsblk"
    export LSBLK_BIN="$TESTDIR/lsblk"

    run detect_removable_drives
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "detect_removable_drives: one candidate" {
    cat > "$TESTDIR/lsblk" <<'MOCK'
#!/usr/bin/env bash
cat <<EOF
nvme0n1 512G disk 0 Samsung SSD
sdb      64G disk 1 Mass Storage Device
EOF
MOCK
    chmod +x "$TESTDIR/lsblk"
    export LSBLK_BIN="$TESTDIR/lsblk"

    run detect_removable_drives
    [ "$status" -eq 0 ]
    # Exactly one /dev/... line.
    local out
    out="$(detect_removable_drives)"
    [ "$(printf '%s\n' "$out" | grep -c '^/dev/')" = "1" ]
    [[ "$(printf '%s\n' "$out" | head -1)" =~ ^/dev/sdb[[:space:]]+64G[[:space:]]+ ]]
}

@test "detect_removable_drives: two candidates" {
    cat > "$TESTDIR/lsblk" <<'MOCK'
#!/usr/bin/env bash
cat <<EOF
nvme0n1 512G disk 0 Samsung SSD
sdb      64G disk 1 SanDisk
sdc      32G disk 1 Kingston DataTraveler
sdb1     63G part 1 SanDisk
EOF
MOCK
    chmod +x "$TESTDIR/lsblk"
    export LSBLK_BIN="$TESTDIR/lsblk"

    local out
    out="$(detect_removable_drives)"
    [ "$(printf '%s\n' "$out" | grep -c '^/dev/')" = "2" ]
}

# ---------------------------------------------------------------------------
# inject_first_boot — produces well-formed TOML + JSON.
# ---------------------------------------------------------------------------

@test "inject_first_boot: writes ssh marker + userconf + custom.toml + credentials.json" {
    local boot="$TESTDIR/boot"
    mkdir -p "$boot"

    run inject_first_boot \
        "$boot" \
        "edge-house" \
        "[1,2]" \
        "RanchWifi" \
        "s3cret-wifi-psk" \
        "mqtt://10.0.0.5:1883" \
        "pi-plaintext-pw"
    [ "$status" -eq 0 ]

    # ssh marker exists (empty)
    [ -f "$boot/ssh" ]

    # userconf.txt has "pi:" prefix and a $6$ SHA-512 crypt hash.
    [ -f "$boot/userconf.txt" ]
    grep -q '^pi:\$6\$' "$boot/userconf.txt"

    # custom.toml contains hostname, ssid, ssh block.
    [ -f "$boot/custom.toml" ]
    grep -q 'hostname = "edge-house"' "$boot/custom.toml"
    grep -q 'ssid = "RanchWifi"' "$boot/custom.toml"
    grep -q 'password = "s3cret-wifi-psk"' "$boot/custom.toml"
    grep -q 'password_encrypted = true' "$boot/custom.toml"

    # skyherd-credentials.json is valid JSON with expected fields.
    [ -f "$boot/skyherd-credentials.json" ]
    jq -e '.edge_id == "edge-house"' "$boot/skyherd-credentials.json"
    jq -e '.wifi_ssid == "RanchWifi"' "$boot/skyherd-credentials.json"
    jq -e '.wifi_psk == "s3cret-wifi-psk"' "$boot/skyherd-credentials.json"
    jq -e '.mqtt_url == "mqtt://10.0.0.5:1883"' "$boot/skyherd-credentials.json"
    jq -e '.trough_ids == [1,2]' "$boot/skyherd-credentials.json"
    jq -e '.ranch_id == "ranch_a"' "$boot/skyherd-credentials.json"
}

@test "inject_first_boot: edge-barn produces trough_ids [3,4,5,6]" {
    local boot="$TESTDIR/boot2"
    mkdir -p "$boot"
    run inject_first_boot \
        "$boot" "edge-barn" "[3,4,5,6]" \
        "RanchWifi" "psk" "mqtt://10.0.0.5:1883" "pi-pw"
    [ "$status" -eq 0 ]
    jq -e '.trough_ids == [3,4,5,6]' "$boot/skyherd-credentials.json"
    jq -e '.edge_id == "edge-barn"' "$boot/skyherd-credentials.json"
}

@test "inject_first_boot: TOML escapes special chars in SSID/PSK" {
    local boot="$TESTDIR/boot3"
    mkdir -p "$boot"
    # A PSK with backslash and quote — both must be escaped in TOML.
    run inject_first_boot \
        "$boot" "edge-house" "[1,2]" \
        'My"Ranch' 'a\b"c' "mqtt://10.0.0.5:1883" "pi-pw"
    [ "$status" -eq 0 ]
    # Escaped in TOML: \" and \\
    grep -q 'ssid = "My\\"Ranch"' "$boot/custom.toml"
    grep -q 'password = "a\\\\b\\"c"' "$boot/custom.toml"
    # Parses cleanly as TOML via python's tomllib.
    run python3 -c "import tomllib,sys; tomllib.load(open('$boot/custom.toml','rb'))"
    [ "$status" -eq 0 ]
}

@test "inject_first_boot: custom.toml parses with python3 tomllib" {
    local boot="$TESTDIR/boot4"
    mkdir -p "$boot"
    run inject_first_boot \
        "$boot" "edge-house" "[1,2]" \
        "RanchWifi" "plainpsk" "mqtt://10.0.0.5:1883" "pi-pw"
    [ "$status" -eq 0 ]
    run python3 -c "
import tomllib
with open('$boot/custom.toml','rb') as f:
    data = tomllib.load(f)
assert data['system']['hostname'] == 'edge-house', data
assert data['user']['name'] == 'pi'
assert data['user']['password_encrypted'] is True
assert data['wlan']['ssid'] == 'RanchWifi'
assert data['wlan']['country'] == 'US'
assert data['ssh']['enabled'] is True
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "inject_first_boot: fails with missing args" {
    run inject_first_boot "" "edge-house" "[1,2]" "s" "p" "m" "pw"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# discover_pi_by_hostname — exit-code paths only (we can't spoof mDNS here).
# ---------------------------------------------------------------------------

@test "discover_pi_by_hostname: returns non-zero on timeout (bogus hostname)" {
    # 2-sec timeout so the test runs fast. We assume no host named
    # skyherd-bats-nonexistent.local on the test LAN.
    run discover_pi_by_hostname "skyherd-bats-nonexistent-$$" 2
    [ "$status" -ne 0 ]
    [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Helpers — json escape.
# ---------------------------------------------------------------------------

@test "_json_escape: backslash + quote + newline" {
    run _json_escape 'a\b"c
d'
    [ "$status" -eq 0 ]
    [ "$output" = 'a\\b\"c\nd' ]
}

@test "_toml_escape: quotes" {
    run _toml_escape 'hello "world"'
    [ "$output" = 'hello \"world\"' ]
}

# ---------------------------------------------------------------------------
# verify_image_sha256 — accepts matching hash, rejects mismatch.
# ---------------------------------------------------------------------------

@test "verify_image_sha256: matching hash passes" {
    echo "contents" > "$TESTDIR/img.bin"
    local hash
    hash="$(sha256sum "$TESTDIR/img.bin" | awk '{print $1}')"
    echo "$hash  img.bin" > "$TESTDIR/img.bin.sha256"
    run verify_image_sha256 "$TESTDIR/img.bin" "$TESTDIR/img.bin.sha256"
    [ "$status" -eq 0 ]
}

@test "verify_image_sha256: mismatched hash fails" {
    echo "contents" > "$TESTDIR/img.bin"
    echo "0000000000000000000000000000000000000000000000000000000000000000  img.bin" > "$TESTDIR/img.bin.sha256"
    run verify_image_sha256 "$TESTDIR/img.bin" "$TESTDIR/img.bin.sha256"
    [ "$status" -ne 0 ]
}
