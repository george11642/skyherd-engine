.PHONY: setup sim demo dashboard dashboard-mock test lint format typecheck clean ci sitl-up sitl-down bus-up bus-down mesh-smoke one-pager hardware-demo hardware-demo-sim hardware-demo-sim-down h2-smoke h3-smoke h4-smoke h4-docs mavic-bridge f3-bridge drone-smoke sitl-smoke determinism-3x gate-check voice-demo rehearsal record-ready preflight

SEED ?= 42
SCENARIO ?= all

setup:
	uv sync --all-extras

sim:
	uv run python -m skyherd.world.cli --seed $(SEED) --duration 300

demo:
	@if [ "$(SCENARIO)" = "all" ]; then \
		uv run skyherd-demo play all --seed $(SEED); \
	else \
		uv run skyherd-demo play $(SCENARIO) --seed $(SEED); \
	fi

dashboard:  ## Build web assets and start live dashboard (real mesh/world/ledger)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	uv run python -m skyherd.server.live --port 8000 --host 127.0.0.1 --seed 42

dashboard-mock:  ## Legacy mock-only dashboard (synthetic events, no sim required)
	(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build) && \
	SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000

web-dev:
	(cd web && pnpm install && pnpm run dev) &
	SKYHERD_MOCK=1 uv run uvicorn skyherd.server.app:app --port 8000 --reload

test:
	uv run pytest --cov=src/skyherd --cov-report=term-missing -q

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

clean:
	rm -rf .venv dist build *.egg-info runtime/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

ci: lint typecheck test

sitl-up:
	docker compose -f docker-compose.sitl.yml up -d --build

sitl-down:
	docker compose -f docker-compose.sitl.yml down

bus-up:
	docker run -d --name skyherd-mosquitto -p 1883:1883 eclipse-mosquitto:2 \
		sh -c 'echo "listener 1883\nallow_anonymous true" > /mosquitto/config/mosquitto.conf && mosquitto -c /mosquitto/config/mosquitto.conf'

bus-down:
	docker stop skyherd-mosquitto && docker rm skyherd-mosquitto

mesh-smoke:
	uv run skyherd-mesh mesh smoke --verbose

one-pager:
	uv run python scripts/render_pdf.py docs/ONE_PAGER.md docs/ONE_PAGER.pdf

hardware-demo:
	@echo "Starting SkyHerd hardware-only demo (coyote hero + sick-cow)..."
	@ANTHROPIC_API_KEY="$(ANTHROPIC_API_KEY)" DRONE_BACKEND="$${DRONE_BACKEND:-mavic}" \
	    HARDWARE_OVERRIDES="$${HARDWARE_OVERRIDES:-trough_cam:trough_1:edge-fence,trough_cam:trough_2:edge-barn}" \
	    uv run skyherd-demo-hw play --prop combo

mavic-bridge:
	uv run python -m skyherd.drone.mavic_bridge

f3-bridge:
	mavlink-router -e 0.0.0.0:14550 /dev/ttyUSB0:115200

drone-smoke:
	DRONE_BACKEND=stub uv run skyherd-drone-smoke

# ---------------------------------------------------------------------------
# Phase 6: SITL-CI & Determinism Gate
# These three targets close BLD-04 (sitl-smoke), SCEN-03 (determinism-3x),
# and SCEN-02 (gate-check).  Phase 4 owns `dashboard` + `dashboard-mock` —
# do NOT edit those here.
# ---------------------------------------------------------------------------

sitl-smoke:  ## BLD-04 proof — real MAVLink mission via pymavlink emulator (<60s)
	uv run python scripts/sitl_smoke.py

determinism-3x:  ## SCEN-03 proof — seed=42 hash-stable across 3 back-to-back runs
	uv run pytest tests/test_determinism_e2e.py -v -m slow --timeout=600

gate-check:  ## SCEN-02 proof — iterates 10 CLAUDE.md Gate items, exit 0 iff 10/10 GREEN
	uv run python scripts/gate_check.py

voice-demo:  ## Render 5 Wes lines (one per urgency) — video B-roll friendly
	SKYHERD_VOICE=$${SKYHERD_VOICE:-mock} uv run skyherd-voice demo

# ---------------------------------------------------------------------------
# Phase 6 (H2): laptop-local hardware-demo sim — desk coyote → SITL takeoff
# ---------------------------------------------------------------------------

hardware-demo-sim:  ## H2 laptop demo: mosquitto + SITL + coyote + pi-to-mission + speaker
	@echo "Starting SkyHerd H2 laptop demo — coyote harness → SITL takeoff → deterrent"
	docker compose -f docker-compose.hardware-demo.yml up -d --build
	@echo ""
	@echo "  Dashboard:  http://localhost:8000"
	@echo "  Tail logs:  docker compose -f docker-compose.hardware-demo.yml logs -f"
	@echo "  Stop stack: make hardware-demo-sim-down"

hardware-demo-sim-down:  ## Stop the H2 laptop demo stack
	docker compose -f docker-compose.hardware-demo.yml down

h2-smoke:  ## Fast unit-level smoke of the H2 chain (<5s, no docker)
	uv run pytest tests/hardware/test_h2_e2e.py -v --no-cov

h3-smoke:  ## Fast unit-level smoke of the H3 Mavic DJI replay chain (<2s, no drone)
	uv run pytest tests/hardware/test_h3_dji_replay.py -v --no-cov

# ---------------------------------------------------------------------------
# Phase 8 (H4): DIY LoRa GPS collar + ChirpStack bridge smoke
# ---------------------------------------------------------------------------

h4-smoke:  ## Fast unit+integration smoke of the H4 collar -> bridge chain (<2s, no collar)
	uv run pytest tests/hardware/test_h4_chirpstack_bridge.py tests/hardware/test_h4_end_to_end.py tests/sensors/test_collar_sim.py -v --no-cov

h4-docs:  ## Print path to the H4 runbook
	@echo "H4 runbook: docs/HARDWARE_H4_RUNBOOK.md"
	@echo "H4 BOM:     hardware/collar/BOM.md"
	@echo "H4 flash:   hardware/collar/flash.sh --help"

# ---------------------------------------------------------------------------
# Phase 9: Demo video rehearsal + record-ready preflight + preflight E2E
# See docs/DEMO_VIDEO_SCRIPT.md for the scrub-points these targets surface.
# ---------------------------------------------------------------------------

rehearsal:  ## VIDEO-06: loop make demo SEED=$(SEED) SCENARIO=$(SCENARIO) for voiceover practice (Ctrl-C to stop)
	@echo "=== SkyHerd rehearsal loop — press Ctrl-C to stop ==="
	@echo "Seed=$(SEED)  Scenario=$(SCENARIO)"
	@while true; do \
		$(MAKE) demo SEED=$(SEED) SCENARIO=$(SCENARIO) || break; \
		echo "--- loop: restarting in 2s (Ctrl-C to stop) ---"; \
		sleep 2; \
	done

record-ready:  ## VIDEO-06: pre-shoot preflight — warm dashboard, print scrub-points, launch at :8000
	@echo "=== SkyHerd record-ready preflight ==="
	@echo "[1/4] Checking dashboard build artifacts..."
	@if [ ! -f web/dist/index.html ]; then \
		echo "    Dashboard not built — building now"; \
		(cd web && (pnpm install --frozen-lockfile || pnpm install) && pnpm run build); \
	else \
		echo "    OK — web/dist/index.html present"; \
	fi
	@echo "[2/4] Seed determinism sanity check (coyote scenario)..."
	@uv run skyherd-demo play coyote --seed $(SEED) >/dev/null 2>&1 \
		&& echo "    OK — coyote scenario runs clean" \
		|| echo "    WARN — coyote scenario exit non-zero (inspect separately)"
	@echo "[3/4] Scrub-points from docs/DEMO_VIDEO_SCRIPT.md:"
	@grep -E '^### [0-9]+:[0-9]+ ' docs/DEMO_VIDEO_SCRIPT.md 2>/dev/null | head -20 || echo "    (script not yet present)"
	@echo "[4/4] Launching dashboard at http://localhost:8000"
	@echo ""
	@echo "=== READY TO RECORD ==="
	@echo "Silence system notifications now. Ctrl-C the dashboard when finished."
	uv run python -m skyherd.server.live --port 8000 --host 127.0.0.1 --seed $(SEED)

preflight:  ## PF-04: run the Phase 9 preflight E2E suite (<30s, fully mocked)
	uv run pytest tests/hardware/test_preflight_e2e.py -v --no-cov --timeout=60
