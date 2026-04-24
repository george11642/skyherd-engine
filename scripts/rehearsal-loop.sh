#!/usr/bin/env bash
# Phase 9 VIDEO-06 — rehearsal loop helper for `make rehearsal`.
#
# Usage:  scripts/rehearsal-loop.sh <SEED> <SCENARIO>
#
# Loops `uv run skyherd-demo play <SCENARIO> --seed <SEED>` until the user
# presses Ctrl-C. Kept as a standalone script so that `make -n rehearsal`
# does not recurse into `$(MAKE) demo` (which, under dry-run, would loop
# indefinitely at the sub-make level).

set -euo pipefail

SEED="${1:-42}"
SCENARIO="${2:-all}"

echo "[rehearsal-loop] seed=${SEED} scenario=${SCENARIO}"

while true; do
    if ! uv run skyherd-demo play "${SCENARIO}" --seed "${SEED}"; then
        echo "[rehearsal-loop] demo exited non-zero, stopping"
        exit 1
    fi
    echo "--- loop: restarting in 2s (Ctrl-C to stop) ---"
    sleep 2
done
