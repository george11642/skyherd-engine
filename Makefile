.PHONY: setup sim demo dashboard dashboard-mock test lint format typecheck clean ci sitl-up sitl-down bus-up bus-down mosquitto-up mosquitto-down mesh-smoke one-pager hardware-demo hardware-demo-sim hardware-demo-sim-down h2-smoke h3-smoke h4-smoke h4-docs mavic-bridge f3-bridge drone-smoke sitl-smoke determinism-3x gate-check voice-demo rehearsal record-ready preflight laptop-drone-smoke edge-pi-setup edge-galileo-setup video-record-clips video-pipeline video-iterate video-iterate-A video-iterate-B video-iterate-C video-iterate-all video-loop video-render video-captions video-captions-A video-captions-B video-captions-C video-style-captions video-style-captions-A video-style-captions-B video-style-captions-C video-broll-sync video-master

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
		sh -c 'printf "listener 1883\nallow_anonymous true\n" > /mosquitto/config/mosquitto.conf && mosquitto -c /mosquitto/config/mosquitto.conf'

bus-down:
	docker stop skyherd-mosquitto && docker rm skyherd-mosquitto

# Aliases — plan & Pi setup script refer to these names.
mosquitto-up: bus-up  ## Alias for bus-up (used by scripts/setup-edge-pi.sh)
mosquitto-down: bus-down  ## Alias for bus-down

edge-pi-setup:  ## Interactive one-command Pi 4 edge bringup (EDGE_ID=edge-house|edge-barn)
	@bash scripts/setup-edge-pi.sh $(EDGE_ID)

edge-galileo-setup:  ## Set up Intel Galileo Gen 1 as edge-tank node (water tank + weather telemetry)
	@bash scripts/setup-edge-galileo.sh

mesh-smoke:
	uv run skyherd-mesh mesh smoke --verbose

web-replay:  ## Capture real sim → web/public/replay.v2.json for faithful browser replay
	uv run python scripts/capture_web_replay.py --seed $(SEED) --out web/public/replay.v2.json
	@echo "Captured $$(wc -c < web/public/replay.v2.json) bytes to web/public/replay.v2.json"

drone-betaflight-smoke:  ## Spin motor 0 at 1200us for 2s via MSP (needs F3 connected, NO PROPS)
	@SKYHERD_DRONE_BACKEND=betaflight \
	 uv run python -m skyherd.drone.betaflight_override --test

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

rehearsal:  ## VIDEO-06: loop `skyherd-demo play` SCENARIO=$(SCENARIO) SEED=$(SEED) for voiceover practice (Ctrl-C to stop)
	@echo "=== SkyHerd rehearsal loop — press Ctrl-C to stop ==="
	@echo "Seed=$(SEED)  Scenario=$(SCENARIO)  (target: demo)"
	@scripts/rehearsal-loop.sh $(SEED) $(SCENARIO)

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
	uv run pytest tests/hardware/test_preflight_e2e.py -v --no-cov

video-record-clips:  ## Record 7+2 dashboard clips for Remotion composition (needs `make record-ready` running)
	uv run --with playwright python scripts/record_dashboard.py --all

# ---------------------------------------------------------------------------
# Phase 7 (demo video automation): autonomous 3-min sim-first demo video.
# See docs/DEMO_VIDEO_AUTOMATION.md for architecture + submission decision tree.
# ---------------------------------------------------------------------------

video-pipeline:  ## VIDEO-FULL: end-to-end — audio → clips → composition → render → package
	@bash scripts/render_vo.sh
	@$(MAKE) video-record-clips
	@cd remotion-video && pnpm install && pnpm run render
	@bash scripts/video_iterate.sh  # (Phase 5 loop — 6-iter cap)
	@$(MAKE) video-render

video-vo:  ## VIDEO-VO: regenerate all 21 vo-*.mp3 via active provider (default: inworld)
	@bash scripts/render_vo.sh

video-vo-elevenlabs:  ## VIDEO-VO-EL: regenerate all VO via ElevenLabs/Will (known-good fallback)
	@SKYHERD_TTS_PROVIDER=elevenlabs bash scripts/render_vo.sh --provider elevenlabs

video-vo-audition:  ## VIDEO-VO-AUD: render 4 Inworld presets + ElevenLabs Will, concat → out/vo-audition.mp3
	@mkdir -p out
	@INWORLD_KEY=$$(grep INWORLD_API_KEY .env.local | cut -d= -f2-) && \
	ELEVENLABS_KEY=$$(grep ELEVENLABS_API_KEY .env.local | cut -d= -f2-) && \
	AUDITION_TEXT="Same ranch. Five Claude Managed Agents, built on Opus 4.7. Every fence, every trough, every cow." && \
	TMP=$$(mktemp -d) && trap "rm -rf $$TMP" EXIT && \
	for VOICE in Jake Avery Nate Tyler; do \
	  PAYLOAD=$$(python3 -c "import json,sys; print(json.dumps({'text':sys.argv[1],'voiceId':sys.argv[2],'modelId':'inworld-tts-1.5-max','audioConfig':{'audioEncoding':'MP3','sampleRateHertz':44100},'temperature':0.8,'applyTextNormalization':'ON'}))" "$$AUDITION_TEXT" "$$VOICE") && \
	  RAW="$$TMP/$$VOICE.raw" && \
	  HTTP=$$(curl -sS -w '%{http_code}' -X POST https://api.inworld.ai/tts/v1/voice \
	    -H "Authorization: Basic $$INWORLD_KEY" -H "Content-Type: application/json" \
	    -o "$$RAW" -d "$$PAYLOAD") && \
	  if [ "$$HTTP" = "200" ]; then \
	    python3 -c "import json,base64,sys; d=json.load(open(sys.argv[1],'rb')); open(sys.argv[2],'wb').write(base64.b64decode(d.get('audioContent','')))" "$$RAW" "$$TMP/$$VOICE.mp3" && \
	    ffmpeg -y -hide_banner -loglevel error -i "$$TMP/$$VOICE.mp3" -ac 2 -ar 44100 -af "loudnorm=I=-18:TP=-1:LRA=11" -c:a libmp3lame -b:a 192k "out/audition-inworld-$$VOICE.mp3" && \
	    echo "[audition] $$VOICE saved"; \
	  else echo "[audition] $$VOICE FAILED HTTP=$$HTTP"; fi; \
	done && \
	ffmpeg -y -hide_banner -loglevel error -f lavfi -i anullsrc=r=44100:cl=stereo -t 1.0 -c:a libmp3lame -b:a 192k "$$TMP/silence.mp3" && \
	( for V in Jake Avery Nate Tyler; do echo "file '$$(pwd)/out/audition-inworld-$$V.mp3'"; echo "file '$$TMP/silence.mp3'"; done ) > "$$TMP/concat.txt" && \
	ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$$TMP/concat.txt" -c:a libmp3lame -b:a 192k -ar 44100 -ac 2 out/vo-audition.mp3 && \
	echo "[audition] out/vo-audition.mp3 ready — edit scripts/vo_voices.json to mark default:true on chosen preset"

video-iterate:  ## VIDEO-ITER: one iteration round for all 3 variants (uses iter-history for iter #)
	@bash scripts/video_iterate.sh A
	@bash scripts/video_iterate.sh B
	@bash scripts/video_iterate.sh C

video-iterate-A:  ## VIDEO-ITER-A: one iteration round for variant A
	@bash scripts/video_iterate.sh A $(if $(ITER),--iter $(ITER),)

video-iterate-B:  ## VIDEO-ITER-B: one iteration round for variant B
	@bash scripts/video_iterate.sh B $(if $(ITER),--iter $(ITER),)

video-iterate-C:  ## VIDEO-ITER-C: one iteration round for variant C
	@bash scripts/video_iterate.sh C $(if $(ITER),--iter $(ITER),)

video-iterate-all:  ## VIDEO-ITER-ALL: parallel iteration for all 3 variants (one round each)
	@bash scripts/video_iterate.sh A & \
	 bash scripts/video_iterate.sh B & \
	 bash scripts/video_iterate.sh C & \
	 wait

video-loop:  ## VIDEO-LOOP: autonomous loop for variant B until ship gate or plateau (max 12 iters)
	@ITER=0; \
	while true; do \
	  ITER=$$((ITER + 1)); \
	  echo "==> video-loop: iter $$ITER/12"; \
	  bash scripts/video_iterate.sh $(or $(VARIANT),B) --iter $$ITER; \
	  CODE=$$?; \
	  if [ $$CODE -eq 2 ]; then echo "SHIP GATE PASSED — stopping loop"; break; fi; \
	  if [ $$CODE -eq 3 ]; then echo "PLATEAU REACHED — stopping loop"; break; fi; \
	  if [ $$CODE -eq 4 ]; then echo "HARD CAP — stopping loop"; break; fi; \
	  if [ $$CODE -ne 0 ]; then echo "ERROR exit $$CODE — stopping loop"; break; fi; \
	  if [ $$ITER -ge 12 ]; then echo "Max 12 iters reached"; break; fi; \
	done

video-render:  ## VIDEO-FINAL: render 1080p60 + loudnorm to -16 LUFS
	@cd remotion-video && pnpm run render
	@ffmpeg -y -i remotion-video/out/skyherd-demo.mp4 -af loudnorm=I=-16:TP=-1:LRA=11 -c:v copy docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4
	@ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4
	@ls -lh docs/demo-assets/video/skyherd-demo-v1-sim-first.mp4

# ---------------------------------------------------------------------------
# Phase 7.1: Laptop-as-drone-controller (no-mobile-app path)
# See docs/LAPTOP_DRONE_CONTROL.md for the Friday workflow + cable spec.
# ---------------------------------------------------------------------------

laptop-drone-smoke:  ## 7.1 LDC-01/03/06: mocked MAVSDK-over-USB-C + manual-override API smoke (<10s, no drone)
	uv run pytest tests/hardware/test_laptop_drone_control.py tests/server/test_drone_control.py -v --no-cov

# ---------------------------------------------------------------------------
# Phase E1: kinetic captions (faster-whisper transcription per variant)
# Sparse mode (A/B) emits emphasis-only windows from the variant scripts;
# dense mode (C) transcribes the full VO bus with word-level timestamps.
# Idempotent — fingerprint check skips re-runs if inputs haven't changed.
# ---------------------------------------------------------------------------

video-captions:  ## E1: regenerate caption JSON for all 3 variants (idempotent)
	uv run python scripts/generate_kinetic_captions.py --variant all

video-captions-A:  ## E1: regenerate captions for variant A only (sparse)
	uv run python scripts/generate_kinetic_captions.py --variant A

video-captions-B:  ## E1: regenerate captions for variant B only (sparse)
	uv run python scripts/generate_kinetic_captions.py --variant B

video-captions-C:  ## E1: regenerate captions for variant C only (dense, ~30s)
	uv run python scripts/generate_kinetic_captions.py --variant C

# ---------------------------------------------------------------------------
# Phase G: Opus 4.7 AI-directed caption styling.
# Reads captions-{A,B,C}.json, asks Claude Opus 4.7 to emit per-word color/
# weight/animation/emphasis_level, writes styled-captions-{A,B,C}.json.
# Prompt-cached system + skills prefix; idempotent fingerprint cache.
# Requires ANTHROPIC_API_KEY (no silent fallback).
# ---------------------------------------------------------------------------

video-style-captions:  ## G: Opus 4.7 styling for all 3 variants (idempotent)
	uv run python scripts/generate_kinetic_captions.py style --variant all

video-style-captions-A:  ## G: Opus 4.7 styling for variant A only
	uv run python scripts/generate_kinetic_captions.py style --variant A

video-style-captions-B:  ## G: Opus 4.7 styling for variant B only
	uv run python scripts/generate_kinetic_captions.py style --variant B

video-style-captions-C:  ## G: Opus 4.7 styling for variant C only
	uv run python scripts/generate_kinetic_captions.py style --variant C

# ---------------------------------------------------------------------------
# Phase 1 (v3): B-roll track sync — regenerate broll-{A,B,C}.json from EDLs.
# Run before each iter render to keep committed JSON in sync with EDL edits.
# fps is always pinned to 30 (Remotion comp rate) regardless of EDL source fps.
# ---------------------------------------------------------------------------

video-broll-sync:  ## Phase1: regenerate remotion-video/src/data/broll-{A,B,C}.json from cinematic EDLs
	uv run python scripts/openmontage_to_remotion.py \
		docs/edl/openmontage-cuts-A-cinematic.json \
		remotion-video/src/data/broll-A.json \
		--emit-broll-track
	uv run python scripts/openmontage_to_remotion.py \
		docs/edl/openmontage-cuts-B-cinematic.json \
		remotion-video/src/data/broll-B.json \
		--emit-broll-track
	uv run python scripts/openmontage_to_remotion.py \
		docs/edl/openmontage-cuts-C-cinematic.json \
		remotion-video/src/data/broll-C.json \
		--emit-broll-track
	@echo "video-broll-sync: broll-A/B/C.json regenerated from cinematic EDLs"

# ---------------------------------------------------------------------------
# Phase 6 S3: post-render two-pass loudnorm mastering + ducking verification.
# Usage: make video-master MP4=out/iter-3/A-iter3.mp4
#   Produces: out/iter-3/A-iter3.mastered.mp4  (loudnorm'd, -16 LUFS, AAC 192k)
#             out/iter-3/A-iter3.mastered.mp4.loudnorm.json  (ffmpeg pass-1 stats)
#             out/iter-3/A-iter3.mastered.vo-segments.json   (VO window sidecar)
# ---------------------------------------------------------------------------

MP4 ?= out/skyherd-demo.mp4

video-master:  ## VIDEO-MASTER: two-pass loudnorm + ducking verify on a rendered MP4
	@if [ -z "$(MP4)" ] || [ ! -f "$(MP4)" ]; then \
		echo "ERROR: MP4=$(MP4) not found. Usage: make video-master MP4=out/iter-N/X-iterN.mp4"; \
		exit 1; \
	fi
	@OUTBASE="$$(echo "$(MP4)" | sed 's/\.mp4$$//')"; \
	MASTERED="$${OUTBASE}.mastered.mp4"; \
	STATS_RAW="$${OUTBASE}.loudnorm-pass1.txt"; \
	STATS_JSON="$${OUTBASE}.loudnorm-pass1.json"; \
	echo "[video-master] Pass 1: measuring loudness of $(MP4)..."; \
	ffmpeg -y -hide_banner \
		-i "$(MP4)" \
		-af "loudnorm=I=-16:TP=-1:LRA=11:print_format=json" \
		-f null - 2>"$${STATS_RAW}"; \
	python3 -c "\
import sys, re, json; \
raw = open(sys.argv[1]).read(); \
m = re.search(r'\{[^}]+\}', raw, re.DOTALL); \
d = json.loads(m.group(0)) if m else {}; \
json.dump(d, open(sys.argv[2], 'w'), indent=2); \
print(d.get('input_i','?'), d.get('input_tp','?'), d.get('input_lra','?'), d.get('input_thresh','?'))\
" "$${STATS_RAW}" "$${STATS_JSON}"; \
	MEASURED_I=$$(python3 -c "import json; d=json.load(open('$${STATS_JSON}')); print(d['input_i'])"); \
	MEASURED_TP=$$(python3 -c "import json; d=json.load(open('$${STATS_JSON}')); print(d['input_tp'])"); \
	MEASURED_LRA=$$(python3 -c "import json; d=json.load(open('$${STATS_JSON}')); print(d['input_lra'])"); \
	MEASURED_THRESH=$$(python3 -c "import json; d=json.load(open('$${STATS_JSON}')); print(d['input_thresh'])"); \
	echo "[video-master] Measured: I=$${MEASURED_I} TP=$${MEASURED_TP} LRA=$${MEASURED_LRA} thresh=$${MEASURED_THRESH}"; \
	echo "[video-master] Pass 2: applying two-pass loudnorm..."; \
	ffmpeg -y -hide_banner -loglevel warning \
		-i "$(MP4)" \
		-af "loudnorm=I=-16:TP=-1:LRA=11:measured_I=$${MEASURED_I}:measured_TP=$${MEASURED_TP}:measured_LRA=$${MEASURED_LRA}:measured_thresh=$${MEASURED_THRESH}:linear=true" \
		-c:v copy -c:a aac -profile:a aac_low -ar 48000 -ac 2 -b:a 192k -movflags +faststart \
		"$${MASTERED}"; \
	echo "[video-master] Mastered: $${MASTERED}"; \
	ls -lh "$${MASTERED}"; \
	echo "[video-master] Running ducking verification..."; \
	bash scripts/verify_ducking.sh "$${MASTERED}"
