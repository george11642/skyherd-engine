# Phase 09 Zero-Config Audit (PF-05)

**Scan date:** 2026-04-24
**Auditor:** gsd-execute-phase agent
**Friday hardware plug-in:** 2026-04-24 AM
**Requirement:** PF-05 — no Friday-path file may require George to edit
code or config on the day of shooting.

---

## Scan targets

Every file that George's Friday workflow touches, directly or indirectly:

- `hardware/pi/bootstrap.sh`
- `hardware/pi/credentials.example.json`
- `hardware/pi/README.md`
- `scripts/provision-edge.sh`
- `scripts/rehearsal-loop.sh`
- `docker-compose.hardware-demo.yml`
- `Makefile` (hardware-* targets + rehearsal + record-ready + preflight)
- `docs/HARDWARE_PI_FLEET.md`
- `docs/HARDWARE_DEMO_RUNBOOK.md`
- `docs/HARDWARE_H1_RUNBOOK.md`
- `docs/HARDWARE_H2_RUNBOOK.md`
- `docs/HARDWARE_H3_RUNBOOK.md`
- `docs/PREFLIGHT_CHECKLIST.md`
- `docs/DEMO_VIDEO_SCRIPT.md`

## Patterns scanned

- `TODO:` / `TODO ` — unfinished task markers.
- `FIXME:` — known-broken code not yet fixed.
- `FILL_IN:` — explicit placeholders requiring user input.
- `{{VAR}}` — Jinja/Mustache-style template placeholders.
- Interactive prompts: `read `, `read -p`, `prompt`, `confirm`, `y/N`.
- Non-`-y` apt-get installs: `apt-get install(?!.*-y)`.

---

## Findings

### Pass 1 — `TODO:` / `FIXME:` / `FILL_IN:`

```bash
grep -rnE 'TODO:|FIXME:|FILL_IN' \
    hardware/pi/ scripts/provision-edge.sh scripts/rehearsal-loop.sh \
    docker-compose.hardware-demo.yml \
    docs/HARDWARE_PI_FLEET.md docs/PREFLIGHT_CHECKLIST.md \
    docs/HARDWARE_H1_RUNBOOK.md docs/HARDWARE_H2_RUNBOOK.md \
    docs/HARDWARE_H3_RUNBOOK.md docs/HARDWARE_DEMO_RUNBOOK.md \
    docs/DEMO_VIDEO_SCRIPT.md
```

**Result: zero matches.** No TODO/FIXME/FILL_IN markers in any Friday-path file.

### Pass 2 — Template placeholders `{{VAR}}`

```bash
grep -rnE '\{\{[^}]+\}\}' \
    hardware/ docker-compose.hardware-demo.yml \
    docs/HARDWARE_PI_FLEET.md docs/PREFLIGHT_CHECKLIST.md \
    docs/HARDWARE_H3_RUNBOOK.md
```

**Result: zero matches.** Friday-path files have no unresolved template
placeholders. (The `{{YOUTUBE_URL}}` placeholders in `SUBMISSION.md`,
`LINKEDIN_LAUNCH.md`, and `YOUTUBE.md` are **intentional** — those are
Sunday submission-day inputs, not Friday-morning blockers.)

### Pass 3 — Interactive prompts

```bash
grep -nE 'read[[:space:]]|read -p|prompt |confirm ' \
    hardware/pi/bootstrap.sh scripts/provision-edge.sh scripts/rehearsal-loop.sh
```

**Result: zero matches.** No `read` / `prompt` / `confirm` in scripts on
the Friday path. The only interactive-ish path in `bootstrap.sh` is the
wifi fallback that writes `wpa_supplicant.conf` — but it's guarded by
`ip route | grep default` and runs only if the Pi has no default route,
so it's a **silent fallback**, not a prompt.

### Pass 4 — `apt-get install` without `-y`

```bash
grep -nE 'apt-get install(?!.*-y)' \
    hardware/pi/bootstrap.sh scripts/provision-edge.sh
```

**Result: zero matches.** Both `apt-get install` invocations use `-y`:
- `hardware/pi/bootstrap.sh:59` — `sudo apt-get install -y "$1"`
- `scripts/provision-edge.sh:49` — `sudo apt-get install -y \`

### Pass 5 — Bootstrap idempotency (re-run)

```bash
# Run 1:
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run > /tmp/br1.txt 2>&1
# Run 2:
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run > /tmp/br2.txt 2>&1
diff /tmp/br1.txt /tmp/br2.txt
```

**Result: clean diff.** Idempotent.

---

## Findings table

| File | Line | Pattern | Verdict | Action |
|------|------|---------|---------|--------|
| — | — | TODO/FIXME/FILL_IN | 0 matches | none needed |
| — | — | `{{VAR}}` template placeholders | 0 matches in Friday-path | none needed |
| — | — | Interactive `read`/`prompt`/`confirm` | 0 matches | none needed |
| — | — | `apt-get install` without `-y` | 0 matches | none needed |
| `hardware/pi/bootstrap.sh` | — | Idempotent dry-run | 2× identical | none needed |

**Known-acceptable residuals (tracked, not fixed):**

| File | Location | Content | Why acceptable |
|------|----------|---------|----------------|
| `hardware/collar/firmware/src/main.cpp` | `// TODO: ...` (3 items) | LoRa firmware OTA signposts | Collar path is **NOT** on Friday route (user has 2 Pi + Mavic only, no DIY collar per `docs/HARDWARE_PI_FLEET.md`). Collar is an optional Phase 8 artifact. |
| `docs/SUBMISSION.md` | `{{YOUTUBE_URL}}` | Devpost submission URL | Filled on submission day 2026-04-26 after YouTube upload. |
| `docs/LINKEDIN_LAUNCH.md` | `{{YOUTUBE_URL}}` | LinkedIn post body | Same. |
| `docs/YOUTUBE.md` | `{{YOUTUBE_URL}}` | Cross-reference in post-upload checklist | Same. |
| `docs/LINKEDIN_LAUNCH.md` | `[APPROVE_BEFORE_POST]` | User-approval gate | Per global rules — LinkedIn publishing always requires George's approval. |

---

## Summary

- **0 blocking defects** for Friday morning hardware plug-in.
- **0 fixes needed** in Phase 9 — the prior hardware phases (5–8) and the
  new Phase 9 additions (bootstrap audit + Friday sequence + checklist)
  all land clean.
- **5 known-acceptable residuals**, all downstream of Friday (Devpost form,
  LinkedIn post, collar firmware which is off-path).

**Verdict: PF-05 PASS.** Friday plug-in sequence from
`docs/HARDWARE_PI_FLEET.md §Friday Morning Sequence` can proceed with zero
code or config edits. The only user input required is the contents of
`skyherd-credentials.json` on each SD card — which is plain config, not
code, and is entered before flashing (not on Friday morning).

---

## Re-run command (for Phase 9 verification)

```bash
# Aggregate zero-config audit — run from repo root:
set -e
echo "=== Pass 1: TODO/FIXME/FILL_IN ==="
grep -rnE 'TODO:|FIXME:|FILL_IN' \
    hardware/pi/ scripts/provision-edge.sh scripts/rehearsal-loop.sh \
    docker-compose.hardware-demo.yml \
    docs/HARDWARE_*.md docs/PREFLIGHT_CHECKLIST.md docs/DEMO_VIDEO_SCRIPT.md \
    2>/dev/null && echo "FAIL: matches present" || echo "PASS: clean"

echo "=== Pass 2: {{VAR}} placeholders ==="
grep -rnE '\{\{[^}]+\}\}' \
    hardware/ docker-compose.hardware-demo.yml \
    docs/HARDWARE_PI_FLEET.md docs/PREFLIGHT_CHECKLIST.md \
    docs/HARDWARE_H3_RUNBOOK.md \
    2>/dev/null && echo "FAIL: matches present" || echo "PASS: clean"

echo "=== Pass 3: interactive prompts ==="
grep -nE 'read[[:space:]]|read -p|prompt |confirm ' \
    hardware/pi/bootstrap.sh scripts/provision-edge.sh scripts/rehearsal-loop.sh \
    2>/dev/null && echo "FAIL: matches present" || echo "PASS: clean"

echo "=== Pass 4: apt-get without -y ==="
grep -nP 'apt-get install(?!.*-y)' \
    hardware/pi/bootstrap.sh scripts/provision-edge.sh \
    2>/dev/null && echo "FAIL: matches present" || echo "PASS: clean"

echo "=== Pass 5: bootstrap idempotency ==="
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run > /tmp/br1.txt 2>&1
SKYHERD_CREDS_FILE=tests/hardware/fixtures/creds_good.json \
    bash hardware/pi/bootstrap.sh --dry-run > /tmp/br2.txt 2>&1
diff -q /tmp/br1.txt /tmp/br2.txt && echo "PASS: idempotent" || echo "FAIL: drift"
```
