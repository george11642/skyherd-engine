# Coding Conventions

**Analysis Date:** 2026-04-22

## Python Style Tooling

**Formatter / Linter:** ruff (configured in `pyproject.toml`)
- Line length: 100 characters
- Target version: Python 3.11
- Rule sets: `E`, `F`, `I`, `B`, `UP`, `N` (pep8, flake8, isort, bugbear, pyupgrade, pep8-naming)
- `E501` (line-length) ignored for docstrings
- `.refs/` directory excluded from lint entirely
- Test files get lenient ignores: `S101`, `B017`, `B905`, `E741`, `F841`, `N806`, `UP017`

**Type Checker:** pyright (configured in `pyproject.toml`)
- Current status: 15 errors, 6 warnings (all in hardware-specific files)
  - `src/skyherd/drone/pymavlink_backend.py`: pymavlink type stubs missing — 7 errors
  - `src/skyherd/drone/sitl_emulator.py`: one `reportOptionalMemberAccess` error
  - `src/skyherd/vision/renderer.py`: `supervision` stubs missing (warning only)
  - `src/skyherd/drone/sitl.py`: `mavsdk` stubs missing (warnings only)
- Core application code (agents, sensors, scenarios, world) passes cleanly

**Current lint status:** 1 ruff error (unsorted import, fixable with `--fix`)

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` — `fenceline_dispatcher.py`, `herd_health_watcher.py`, `sitl_emulator.py`
- Test files: `test_<module_name>.py` — mirrors source structure exactly
- Skills: `kebab-case.md` inside domain subdirectory — `skills/predator-ids/coyote.md`

**Classes:**
- `PascalCase` throughout — `FenceMotionSensor`, `SessionManager`, `AgentSpec`, `SkyHerdSSE`
- Exceptions: `PascalCase` ending in `Error` or using established names — `DroneUnavailable`, `GeofenceViolation`

**Functions/Methods:**
- `snake_case` for all functions — `get_bus_state()`, `build_cached_messages()`, `_mqtt_topic_matches()`
- Private helpers prefixed with `_` — `_simulate_handler()`, `_iso()`, `_load_text()`
- Boolean-returning helpers: `is_`/`has_`/`can_` prefix not enforced; some use plain names (`fence_breached_by`)

**Variables:**
- `snake_case` — `session_id`, `wake_event`, `ranch_id`
- Module-level constants: `UPPER_SNAKE_CASE` — `_DEFAULT_BROKER_PORT`, `_DEBOUNCE_S`, `_STEP_DT`
  - Private constants prefixed with `_` even when `UPPER_SNAKE_CASE`
- Exported spec constants: all-caps no underscore prefix — `FENCELINE_DISPATCHER_SPEC`

**TypeScript/React:**
- Components: `PascalCase` — `AgentLane`, `CostTicker`, `AttestationPanel`
- Props interfaces: `{ComponentName}Props` — `AgentLaneProps`, `AgentLaneProps`
- Utility files: `camelCase.ts` — `cn.ts`, `sse.ts`, `replay.ts`
- Constants/records: `UPPER_SNAKE_CASE` — `AGENT_SHORT`, `MAX_SPARKLINE`

## Typing Discipline

**Python:**
- `from __future__ import annotations` used in 88 of 101 source files — near-universal
- `TYPE_CHECKING` guards for circular imports — standard pattern:
  ```python
  # src/skyherd/sensors/fence.py:8-16
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from skyherd.attest.ledger import Ledger
      from skyherd.sensors.bus import SensorBus
  ```
- Return types on all public functions — `async def tick(self) -> None`
- `Any` used sparingly and only where truly necessary (`sdk_client: Any`, `wake_event: dict[str, Any]`)
- `type: ignore[assignment]` used 5 times for `tuple()` casts where pymavlink types don't have stubs
- No bare `type: ignore` without inline justification comment

**TypeScript:**
- Strict mode via `tsconfig.json` (inferred from `tsc -b` in build)
- All component props explicitly typed with named interfaces
- `any` appears only twice in `src/lib/sse.ts` with `// eslint-disable-next-line` comments
- Shared interfaces defined at component level (`AgentCost`, `CostTickPayload`)
- No `React.FC` usage — plain function components throughout

## Import Organization

**Python pattern (consistent across all modules):**
1. `from __future__ import annotations` (always first)
2. Standard library imports
3. Third-party imports
4. Local `skyherd` imports
5. `TYPE_CHECKING` block at end of imports

```python
# src/skyherd/agents/fenceline_dispatcher.py:30-38
from __future__ import annotations

import logging
import os
from typing import Any

from skyherd.agents._handler_base import run_handler_cycle
from skyherd.agents.session import Session, _load_text, build_cached_messages
```

**Lazy imports:** Used for optional/heavy dependencies loaded at runtime
```python
# src/skyherd/agents/fenceline_dispatcher.py:144
from skyherd.agents.mesh_neighbor import _simulate_neighbor_handler
```

**TypeScript:**
- Path alias `@` maps to `web/src/` — configured in `vite.config.ts`
- All imports use `@/` prefix for internal modules: `import { cn } from "@/lib/cn"`
- External packages first, then `@/` internal

## Async/Await Usage

- `asyncio.mode = "auto"` in pytest — all `async def test_*` functions run without `@pytest.mark.asyncio` decorator
- Sensor base class pattern: `async def tick(self) -> None` + `async def run(self) -> None` (cancelable loop)
- `asyncio.CancelledError` explicitly re-raised in sensor loops — not swallowed
- SSE server uses async generators for event streaming (`src/skyherd/server/events.py`)
- `asynccontextmanager` used for resource management in bus (`src/skyherd/sensors/bus.py`)
- Background tasks via `asyncio.Task` — not bare `asyncio.create_task` without capture

## Error Handling Patterns

**Python — broad catches are documented:**
- `except Exception as exc:  # noqa: BLE001` — used throughout for non-fatal background tasks
  - Present in: `src/skyherd/agents/mesh.py`, `src/skyherd/server/events.py`, `src/skyherd/agents/cost.py`
  - Always logs the exception before swallowing: `logger.warning("...", exc)`
- `except Exception as exc:  # noqa: BLE001` pattern signals intentional broad catch, not carelessness
- Specific exceptions raised for public API errors: `KeyError`, `FileNotFoundError`, `ValueError`
- Custom exceptions in `src/skyherd/drone/interface.py`: `DroneUnavailable`, `GeofenceViolation`, `BatteryTooLow`, `WindTooHigh`

**Python — error propagation:**
- Internal helpers raise — callers catch or propagate
- `SessionManager._get()` raises `KeyError` with context: `raise KeyError(f"Unknown session: {session_id}") from None`
- `_load_text()` returns empty string on missing file + logs warning — never raises

**TypeScript — SSE errors:**
- Malformed JSON silently ignored in `src/lib/sse.ts` with inline comment
- `onerror` handler drives reconnect with exponential backoff (1s → 30s cap)

## Logging

**Python:**
- Module-level logger: `logger = logging.getLogger(__name__)` — in every source module with logging
- No `print()` statements in library code
- Log levels used correctly: `DEBUG` for trace/lifecycle, `INFO` for state transitions, `WARNING` for anomalies/breach events, `ERROR` not used directly (caught and re-logged as `WARNING`)
- `%s`-style string formatting (not f-strings) in log calls — avoids eager evaluation

## MQTT Topic Conventions

**Topic structure:** `skyherd/{ranch_id}/{sensor_type}/{entity_id}`

Examples from source:
- `skyherd/{ranch_id}/{self.topic_prefix}/{entity_id}` — computed in `Sensor.__init__` (`src/skyherd/sensors/base.py:60`)
- `skyherd/+/fence/+` — wake topic wildcard in `FENCELINE_DISPATCHER_SPEC`
- `skyherd/+/thermal/+` — thermal wake topic
- `skyherd/neighbor/+/+/predator_confirmed` — cross-ranch mesh topic

**Event payload fields** (consistent across sensor types):
- `ts`: float timestamp (via `ts_provider`)
- `kind`: event type string (e.g., `"fence.breach"`, `"water.tank"`)
- `ranch`: ranch identifier
- `entity`: entity identifier

## Skills-First Architecture Discipline

**Pattern is real and consistently applied.** Domain knowledge lives in `skills/` Markdown files, not in agent system prompts.

**Skills library:** 33 files across 6 domains in `skills/`
- `skills/predator-ids/` — coyote, mountain-lion, wolf, livestock-guardian-dogs, thermal-signatures
- `skills/cattle-behavior/` — lameness, calving, disease (7 heads), feeding, herd-structure
- `skills/drone-ops/` — patrol-planning, deterrent-protocols, battery-economics, no-fly-zones
- `skills/ranch-ops/` — fence-line-protocols, human-in-loop-etiquette, paddock-rotation, part-107-rules, water-tank-sops
- `skills/nm-ecology/` — predator ranges, forage, seasonal calendar, weather patterns
- `skills/voice-persona/` — wes-register, urgency-tiers, never-panic

**How skills are wired in agents:**
- `AgentSpec.skills` field lists file paths: `src/skyherd/agents/spec.py:50`
- Skills loaded at wake time via `_load_text()` and sent as `cache_control: {"type": "ephemeral"}` blocks
- Each agent has a concise inline system prompt + a `system_prompt_template_path` for the stable prompt
- Example from `src/skyherd/agents/fenceline_dispatcher.py:53-78`: 12 skill files declared — predator IDs, fence protocols, drone ops, voice persona

**System prompts are short:** The `_SYSTEM_PROMPT_INLINE` in `fenceline_dispatcher.py` is 7 lines; skills carry the domain knowledge.

## Component Organization (Frontend)

**Structure:**
- Feature components: `web/src/components/*.tsx` — co-located with `.test.tsx`
- Shared primitives: `web/src/components/shared/` — `Chip`, `MonoText`, `PulseDot`, `ScenarioStrip`, `StatBand`
- shadcn/ui primitives: `web/src/components/ui/` — `badge`, `button`, `card`, `sheet`, `table`, `tooltip`
- Utilities: `web/src/lib/` — `cn.ts` (clsx+tailwind-merge), `sse.ts`, `replay.ts`

**React 19 patterns:**
- All components are plain functions — no class components, no `React.FC`
- `useRef` + `useEffect` for auto-scroll: `web/src/components/AgentLane.tsx:43-50`
- Framer Motion used for animated counters in `CostTicker` — not for layout transitions
- SSE data flows via global singleton `getSSE()` — no React context, just event subscriptions in `useEffect`

**Tailwind v4 usage:**
- CSS variables for design tokens: `var(--color-text-0)`, `var(--color-line)`, `var(--font-mono)`, `var(--font-display)`
- Utility classes mixed with inline `style` props for dynamic colors — not a clean split
- `cn()` helper (`clsx` + `tailwind-merge`) used for conditional classes
- Custom utilities defined in `web/src/index.css`: `chip`, `chip-sage`, `chip-sky`, `chip-muted`, `log-scroll`, `tabnum`, `pulse-dot`

---

*Convention analysis: 2026-04-22*
