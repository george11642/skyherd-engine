"""CLI entry-point for the SkyHerd Edge runtime.

Commands
--------
skyherd-edge run
    Start the EdgeWatcher capture/detect/publish loop.
skyherd-edge smoke
    Smoke test: capture one mock frame, publish, exit 0.
skyherd-edge picam
    Run the PiCamSensor (pinkeye pixel classifier on every frame).
skyherd-edge coyote
    Run the CardboardCoyoteHarness (plays a thermal clip over MQTT).
skyherd-edge verify-bootstrap
    Parse a credentials.json and report missing fields.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import typer

app = typer.Typer(name="skyherd-edge", help="SkyHerd Pi H1 edge runtime.")

_REQUIRED_CRED_FIELDS: tuple[str, ...] = (
    "wifi_ssid",
    "wifi_psk",
    "mqtt_url",
    "ranch_id",
    "edge_id",
    "trough_ids",
)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def run(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Start the EdgeWatcher capture/detect/publish loop."""
    _configure_logging(verbose)
    from skyherd.edge.watcher import EdgeWatcher

    watcher = EdgeWatcher()
    asyncio.run(watcher.run())


@app.command()
def smoke(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Smoke test: capture one mock frame, publish in-process, exit 0 on success."""
    _configure_logging(verbose)
    from skyherd.edge.camera import MockCamera
    from skyherd.edge.detector import RuleDetector
    from skyherd.edge.watcher import EdgeWatcher

    async def _run() -> None:
        # Use in-process mock — no broker required for smoke
        watcher = EdgeWatcher(
            camera=MockCamera(),
            detector=RuleDetector(),
            ranch_id="ranch_smoke",
            edge_id="smoke_node",
            mqtt_url="mqtt://localhost:19999",  # unreachable by design — publish is best-effort
            capture_interval_s=1.0,
        )
        payload = await watcher.run_once()
        count = len(payload.get("detections", []))
        typer.echo(f"smoke ok — 1 mock frame published, {count} detection(s)")

    try:
        asyncio.run(_run())
    except Exception as exc:
        typer.echo(f"smoke FAILED: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# verify-bootstrap — parse credentials.json and report missing fields
# ---------------------------------------------------------------------------


@app.command("verify-bootstrap")
def verify_bootstrap(
    credentials_file: Path = typer.Option(
        Path("/boot/firmware/skyherd-credentials.json"),
        "--credentials-file",
        "-c",
        help="Path to the credentials.json file.",
    ),
) -> None:
    """Parse credentials.json; exit 0 if all required fields present, exit 2 otherwise.

    Used by hardware/pi/bootstrap.sh to fail-fast before provisioning.
    Required fields: wifi_ssid, wifi_psk, mqtt_url, ranch_id, edge_id, trough_ids.
    """
    if not credentials_file.exists():
        typer.echo(f"credentials file not found: {credentials_file}", err=True)
        raise typer.Exit(code=2)

    try:
        raw = credentials_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in {credentials_file}: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        typer.echo(f"Could not read {credentials_file}: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    if not isinstance(data, dict):
        typer.echo(
            f"Invalid JSON in {credentials_file}: expected object, got {type(data).__name__}",
            err=True,
        )
        raise typer.Exit(code=2)

    missing = [f for f in _REQUIRED_CRED_FIELDS if not data.get(f)]
    if missing:
        typer.echo(f"Missing fields: {', '.join(missing)}", err=True)
        raise typer.Exit(code=2)

    typer.echo(f"verify-bootstrap OK — {credentials_file} has all required fields.")


# ---------------------------------------------------------------------------
# picam — run the PiCamSensor loop
# ---------------------------------------------------------------------------


@app.command()
def picam(
    cam_id: str = typer.Option("picam_0", "--cam-id", help="Camera identifier."),
    ranch_id: str = typer.Option("ranch_a", "--ranch-id", help="Ranch identifier."),
    mqtt_url: str = typer.Option(
        "mqtt://localhost:1883", "--mqtt-url", help="MQTT broker URL."
    ),
    interval_s: float = typer.Option(10.0, "--interval-s", help="Seconds between captures."),
    seed: int | None = typer.Option(
        None, "--seed", help="Deterministic frame-ordering seed (dev-mode only)."
    ),
    max_ticks: int | None = typer.Option(
        None, "--max-ticks", help="Run for N ticks, then exit (test mode)."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the PiCamSensor loop (pinkeye pixel classifier on every frame)."""
    _configure_logging(verbose)
    try:
        from skyherd.edge.picam_sensor import PiCamSensor
    except ImportError as exc:
        typer.echo(
            f"picam subcommand unavailable — skyherd.edge.picam_sensor missing ({exc}).\n"
            "This should not happen on a fully-installed skyherd-engine.",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    sensor = PiCamSensor(
        cam_id=cam_id,
        ranch_id=ranch_id,
        mqtt_url=mqtt_url,
        capture_interval_s=interval_s,
        seed=seed,
    )

    if max_ticks is not None:

        async def _bounded() -> None:
            for _ in range(max_ticks):
                payload = await sensor.run_once()
                typer.echo(
                    f"picam tick — ts={payload['ts']:.3f} "
                    f"pinkeye={payload.get('pinkeye_result', {}).get('severity')} "
                    f"cows_present={payload['cows_present']}"
                )
            sensor.close()

        asyncio.run(_bounded())
    else:
        try:
            asyncio.run(sensor.run())
        finally:
            sensor.close()


# ---------------------------------------------------------------------------
# coyote — run the CardboardCoyoteHarness
# ---------------------------------------------------------------------------


@app.command()
def coyote(
    cam_id: str = typer.Option("coyote_cam", "--cam-id", help="Thermal camera ID."),
    ranch_id: str = typer.Option("ranch_a", "--ranch-id", help="Ranch identifier."),
    mqtt_url: str = typer.Option(
        "mqtt://localhost:1883", "--mqtt-url", help="MQTT broker URL."
    ),
    interval_s: float = typer.Option(
        2.0, "--interval-s", help="Seconds between thermal frames."
    ),
    seed: int | None = typer.Option(None, "--seed", help="Deterministic-playback seed."),
    max_ticks: int | None = typer.Option(
        None, "--max-ticks", help="Emit N frames, then exit."
    ),
    clip_dir: Path | None = typer.Option(
        None, "--clip-dir", help="Override thermal clip directory."
    ),
    species: str = typer.Option("coyote", "--species", help="Reported predator species."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the CardboardCoyoteHarness — plays a thermal clip over MQTT."""
    _configure_logging(verbose)
    try:
        from skyherd.edge.coyote_harness import CoyoteHarness
    except ImportError as exc:
        typer.echo(
            f"coyote subcommand unavailable — skyherd.edge.coyote_harness missing ({exc}).\n"
            "This should not happen on a fully-installed skyherd-engine.",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    harness = CoyoteHarness(
        cam_id=cam_id,
        ranch_id=ranch_id,
        mqtt_url=mqtt_url,
        interval_s=interval_s,
        seed=seed,
        clip_dir=clip_dir,
        species=species,
    )

    if max_ticks is not None:

        async def _bounded() -> None:
            for _ in range(max_ticks):
                payload = await harness.run_once()
                typer.echo(
                    f"coyote tick — ts={payload['ts']:.3f} "
                    f"frame_idx={payload.get('frame_idx')} "
                    f"predators={payload['predators_detected']}"
                )

        asyncio.run(_bounded())
    else:
        asyncio.run(harness.run())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
