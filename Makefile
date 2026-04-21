.PHONY: setup sim demo dashboard test lint format typecheck clean ci sitl-up sitl-down bus-up bus-down mesh-smoke

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

dashboard:
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
