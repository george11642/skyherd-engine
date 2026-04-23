#!/usr/bin/env bash
# fresh_clone_smoke.sh — verify the README 3-command quickstart on a clean checkout.
#
# Usage:
#   bash scripts/fresh_clone_smoke.sh
#
# Exits 0 if the full quickstart completes successfully; non-zero on any failure.
# Target runtime: < 5 min on a cold Ubuntu GitHub Actions runner.
#
# Environment variables:
#   GITHUB_WORKSPACE  — repo root to clone from (default: $(pwd))

set -euo pipefail

START=$(date +%s)
SANDBOX=$(mktemp -d -t skyherd-smoke.XXXXXX)
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$SANDBOX"
}
trap cleanup EXIT INT TERM

SOURCE_REPO="${GITHUB_WORKSPACE:-$(pwd)}"

echo "===> [smoke] sandbox: $SANDBOX"
echo "===> [smoke] source:  $SOURCE_REPO"

# Step 0: clone via file:// (simulates fresh clone without touching origin)
git clone --depth 1 "file://${SOURCE_REPO}" "$SANDBOX/repo"
cd "$SANDBOX/repo"

echo "===> [smoke] step 1: uv sync"
uv sync

echo "===> [smoke] step 2: pnpm install + build"
(cd web && pnpm install --frozen-lockfile && pnpm run build)

echo "===> [smoke] step 3: make demo SEED=42 SCENARIO=all"
timeout 180 make demo SEED=42 SCENARIO=all

echo "===> [smoke] step 4: dashboard /health probe (generic server — Plan 02 independent)"
# Use the stable generic server entry-point — decouples smoke from whether
# make dashboard is live or mock (Phase 4 Plan 02 flips that default).
uv run uvicorn skyherd.server.app:app --port 18765 --log-level warning &
SERVER_PID=$!

# Poll /health for up to 20s
for i in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:18765/health" > /dev/null 2>&1; then
        echo "===> [smoke] /health OK after ${i}s"
        break
    fi
    sleep 1
    if [ "$i" -eq 20 ]; then
        echo "===> [smoke] FAIL: /health never responded"
        exit 1
    fi
done

# Bonus: probe /api/snapshot returns 200 (mock or live both serve it)
curl -sf "http://127.0.0.1:18765/api/snapshot" > /dev/null || {
    echo "===> [smoke] FAIL: /api/snapshot did not respond"
    exit 1
}

END=$(date +%s)
echo "===> [smoke] PASS in $((END - START))s"
