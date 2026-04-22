T16: stable — ruff clean, 1106 tests at 87.42% (80% passed), 16/16 demo PASSes (seed 42), HTTP 200. 2026-04-21.

# T15 Stability Note — 20260421-000000

HEAD `efa0c2f239bdc49fcd6b53beb4c52c8a68caf6c5` — ruff clean, 1106 tests at 87.42% coverage (80% threshold passed), 16/16 demo PASSes (seed 42), prod endpoint `https://skyherd-engine.vercel.app` HTTP 200. No regression from T14. System stable at 9/10 gate TRULY-GREEN.

---

# T14 Stability Note — 20260422-091631

HEAD `c4ad982397e8e23eb6c3410646e5774610430ded` — ruff clean, 1106 tests at 87.42% coverage (80% threshold passed), all 8/8 SITL scenarios PASS (seed 42), prod endpoint `https://skyherd-engine.vercel.app` HTTP 200. No regression from T13. System stable at 9/10 gate.

---

# Verify Loop T13 — 20260422-085000

Generated: 2026-04-22T08:50:00Z
Loop tag: **T13**
Operator: verify-loop-T13

---

No regression since T12. System stable at 9/10 Gate TRULY-GREEN.

HEAD `4797ae9afc31a6891edfcac72da5277c94e3bbb9` — ruff clean, 1106 tests at 87.41% coverage (80% threshold passed), all 8/8 SITL scenarios PASS (seed 42), and prod endpoint `https://skyherd-engine.vercel.app` returns HTTP 200. Zero new issues detected; the pre-existing 15 pyright third-party-stub warnings and wall-clock float determinism yellow remain unchanged from prior loops. Submission-ready for Apr 26 deadline.

---

## 1. HEAD + GREEN/TOTAL

**HEAD**: `4797ae9afc31a6891edfcac72da5277c94e3bbb9`

**Commit**: `docs: verify loop T12 — no regression, 1106 tests 87%, SITL PASS, 8/8 scenarios, 9/10 gate stable`

**Recent trail (last 5)**:
```
4797ae9 docs: verify loop T12 — no regression, 1106 tests 87%, SITL PASS, 8/8 scenarios, 9/10 gate stable
0aa71d7 docs: verify loop T11 — 385b864 HEAD, 1106 tests 87%, SITL PASS, 8/8 scenarios, all gates confirmed
385b864 fix(gitignore): .refs/ + runtime/ properly ignored (undo accidental submodule gitlinks)
77d29cb chore(lint): ruff format pass across test files (T10 yellow cleanup)
b57fef9 docs: verify loop T10 — 1106 tests 87%, SITL PASS, 8/8 scenarios, R3/R2a/C1 closed
```

**Tests**: 1106 passed, 13 skipped, 2 warnings — **87.41% coverage** (required 80%)

---

## 2. Lint / Type / Test Tails

### ruff check
```
All checks passed!
```

### pytest (tail)
```
TOTAL  5789  729  87%
Required test coverage of 80% reached. Total coverage: 87.41%
1106 passed, 13 skipped, 2 warnings in 142.51s
```

---

## 3. Scenarios (8/8)

```
Results: 8/8 passed
  coyote              PASS  (0.38s wall, 131 events)
  sick_cow            PASS  (1.41s wall,  62 events)
  water_drop          PASS  (0.32s wall, 121 events)
  calving             PASS  (0.47s wall, 123 events)
  storm               PASS  (0.38s wall, 124 events)
  cross_ranch_coyote  PASS  (0.41s wall, 131 events)
  wildfire            PASS  (0.42s wall, 122 events)
  rustling            PASS  (0.42s wall, 123 events)
```

---

## 4. Prod Endpoints

| Endpoint | Status |
|----------|--------|
| `https://skyherd-engine.vercel.app` | HTTP 200 |

---

## 5. Gate Summary vs T12

| Gate | T12 | T13 | Delta |
|------|-----|-----|-------|
| ruff check | GREEN | GREEN | none |
| ruff format | GREEN | GREEN | none |
| pyright | YELLOW (15 pre-existing) | YELLOW (15 pre-existing) | none |
| Tests / coverage | GREEN 87.41% | GREEN 87.41% | none |
| 8/8 scenarios | GREEN | GREEN | none |
| Vercel prod | GREEN | GREEN | none |
| Determinism (G8) | YELLOW (wall-clock float) | YELLOW (unchanged) | none |

**REGRESSION COUNT: 0**

---

## 6. Final Verdict

**No regression since T12. System holds at 9/10 Gate TRULY-GREEN.**

Submission-ready for Apr 26 deadline. Remaining open items unchanged: determinism byte-identity (cosmetic), submission summary text (100-200 words), and the cerebralvalley.ai form. No code or test changes were needed this loop.
