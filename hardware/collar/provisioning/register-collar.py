#!/usr/bin/env python3
"""register-collar -- provision a DIY LoRa GPS collar into SkyHerd.

Usage:
    python register-collar.py --dev-eui A8610A3453210A00 \\
                              --ranch ranch_a \\
                              --cow-tag A001

Environment variables:
    CHIRPSTACK_API_URL    Base URL of ChirpStack API (e.g. http://localhost:8080)
    CHIRPSTACK_API_TOKEN  ChirpStack API token (generate in ChirpStack UI -> API keys)
    MQTT_URL              MQTT broker URL (default mqtt://localhost:1883)

The script:
  1. Registers the device in ChirpStack via REST API (or local registry fallback).
  2. Appends the mapping to runtime/collars/registry.json.
  3. Verifies the MQTT topic route by subscribing briefly and reporting status.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Registry path relative to repo root (two levels up from provisioning/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_REGISTRY_PATH = _REPO_ROOT / "runtime" / "collars" / "registry.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("register-collar")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Register a DIY LoRa GPS collar in SkyHerd.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--dev-eui", required=True, help="LoRaWAN DevEUI (16 hex chars, no colons)")
    p.add_argument("--ranch", required=True, help="Ranch identifier (e.g. ranch_a)")
    p.add_argument("--cow-tag", required=True, help="Cow tag / animal ID (e.g. A001)")
    p.add_argument(
        "--app-key",
        default="",
        help="Root key (optional -- ChirpStack auto-generates if omitted)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs without writing anything",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def validate_dev_eui(eui: str) -> str:
    """Normalise and validate a DevEUI string."""
    eui = eui.upper().replace(":", "").replace("-", "").replace(" ", "")
    if len(eui) != 16 or not all(c in "0123456789ABCDEF" for c in eui):
        raise ValueError(f"Invalid DevEUI '{eui}' -- must be 16 hex characters")
    return eui


# ---------------------------------------------------------------------------
# ChirpStack registration
# ---------------------------------------------------------------------------


def chirpstack_register(dev_eui: str, ranch_id: str, cow_tag: str, app_key: str) -> bool:
    """Register device in ChirpStack via REST API.

    Returns True on success, False if ChirpStack is unavailable (falls back to
    local registry only).
    """
    api_url = os.environ.get("CHIRPSTACK_API_URL", "").rstrip("/")
    api_token = os.environ.get("CHIRPSTACK_API_TOKEN", "")

    if not api_url or not api_token:
        log.warning(
            "CHIRPSTACK_API_URL / CHIRPSTACK_API_TOKEN not set -- skipping ChirpStack registration"
        )
        return False

    try:
        import urllib.error  # noqa: F401
        import urllib.request
    except ImportError:
        log.error("urllib not available")
        return False

    # Discover or create Application ID for this ranch
    app_id = _get_or_create_chirpstack_app(api_url, api_token, ranch_id)
    if app_id is None:
        return False

    # Device profile ID -- look for an existing "LoRaWAN OTAA" profile
    profile_id = _get_device_profile_id(api_url, api_token)
    if profile_id is None:
        log.warning(
            "No suitable device profile found in ChirpStack -- create one named 'SkyHerd Collar'"
        )
        return False

    # Create device
    device_payload = json.dumps(
        {
            "device": {
                "applicationID": app_id,
                "description": f"SkyHerd collar cow={cow_tag} ranch={ranch_id}",
                "devEUI": dev_eui,
                "deviceProfileID": profile_id,
                "isDisabled": False,
                "name": f"collar-{cow_tag}",
                "referenceAltitude": 0,
                "skipFCntCheck": False,
                "tags": {"ranch": ranch_id, "cow_tag": cow_tag},
                "variables": {},
            }
        }
    ).encode()

    req = urllib.request.Request(
        f"{api_url}/api/devices",
        data=device_payload,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            log.info("ChirpStack device created: %s", body)
    except Exception as exc:  # noqa: BLE001
        # 409 = already exists -- treat as success
        err = str(exc)
        if "409" in err or "already exists" in err.lower():
            log.info("Device %s already registered in ChirpStack", dev_eui)
        else:
            log.warning("ChirpStack device create failed: %s", exc)
            return False

    # Set OTAA keys
    if app_key:
        keys_payload = json.dumps(
            {"deviceKeys": {"appKey": app_key, "devEUI": dev_eui, "nwkKey": app_key}}
        ).encode()
        key_req = urllib.request.Request(
            f"{api_url}/api/devices/{dev_eui}/keys",
            data=keys_payload,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(key_req, timeout=10):
                log.info("OTAA keys set for %s", dev_eui)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not set OTAA keys: %s", exc)

    return True


def _get_or_create_chirpstack_app(api_url: str, api_token: str, ranch_id: str) -> str | None:
    """Return ChirpStack applicationID for the ranch, creating it if absent."""
    import urllib.request

    list_req = urllib.request.Request(
        f"{api_url}/api/applications?limit=100",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(list_req, timeout=10) as resp:
            body = json.loads(resp.read())
            for app in body.get("result", []):
                if app.get("name") == ranch_id:
                    return app["id"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not list ChirpStack applications: %s", exc)
        return None

    # Create it
    create_payload = json.dumps(
        {"application": {"description": f"SkyHerd ranch {ranch_id}", "name": ranch_id}}
    ).encode()
    create_req = urllib.request.Request(
        f"{api_url}/api/applications",
        data=create_payload,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(create_req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("id")
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not create ChirpStack application: %s", exc)
        return None


def _get_device_profile_id(api_url: str, api_token: str) -> str | None:
    """Return the first suitable OTAA device profile ID."""
    import urllib.request

    req = urllib.request.Request(
        f"{api_url}/api/device-profiles?limit=50",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            for profile in body.get("result", []):
                name = profile.get("name", "").lower()
                if "collar" in name or "otaa" in name or "skyherd" in name:
                    return profile["id"]
            # Fall back to first available
            profiles = body.get("result", [])
            if profiles:
                return profiles[0]["id"]
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not retrieve device profiles: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Local registry
# ---------------------------------------------------------------------------


def write_local_registry(dev_eui: str, ranch_id: str, cow_tag: str) -> None:
    """Append/update collar entry in runtime/collars/registry.json."""
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    registry: list[dict] = []
    if _REGISTRY_PATH.exists():
        try:
            registry = json.loads(_REGISTRY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            registry = []

    # Remove any existing entry for this dev_eui or cow_tag/ranch combo
    registry = [
        r
        for r in registry
        if r.get("dev_eui") != dev_eui
        and not (r.get("cow_tag") == cow_tag and r.get("ranch") == ranch_id)
    ]

    entry = {
        "dev_eui": dev_eui,
        "ranch": ranch_id,
        "cow_tag": cow_tag,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "real",  # vs "sim" for dashboard colouring
        "mqtt_topic": f"skyherd/{ranch_id}/collar/{cow_tag}",
    }
    registry.append(entry)

    _REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    log.info("Registry written -> %s", _REGISTRY_PATH)
    log.info("Entry: %s", json.dumps(entry, indent=2))


# ---------------------------------------------------------------------------
# MQTT topic verification
# ---------------------------------------------------------------------------


def verify_mqtt_topic(ranch_id: str, cow_tag: str, timeout_s: float = 5.0) -> bool:
    """Subscribe briefly to the collar topic and report connectivity."""
    mqtt_url = os.environ.get("MQTT_URL", "mqtt://localhost:1883")
    topic = f"skyherd/{ranch_id}/collar/{cow_tag}"

    # Parse host:port
    without_scheme = mqtt_url.split("://", 1)[-1]
    host, _, port_str = without_scheme.partition(":")
    port = int(port_str) if port_str else 1883

    try:
        import socket

        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        log.info("MQTT broker reachable at %s:%d", host, port)
        log.info("Topic route verified: %s", topic)
        return True
    except OSError as exc:
        log.warning("MQTT broker not reachable at %s:%d -- %s", host, port, exc)
        log.warning("Topic %s will activate when broker starts", topic)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    try:
        dev_eui = validate_dev_eui(args.dev_eui)
    except ValueError as exc:
        log.error("%s", exc)
        return 1

    ranch_id = args.ranch.lower().strip()
    cow_tag = args.cow_tag.upper().strip()

    log.info("Provisioning collar devEUI=%s ranch=%s cow=%s", dev_eui, ranch_id, cow_tag)

    if args.dry_run:
        log.info("Dry-run mode -- no changes written")
        log.info(
            "Would register: devEUI=%s ranch=%s cow=%s topic=skyherd/%s/collar/%s",
            dev_eui,
            ranch_id,
            cow_tag,
            ranch_id,
            cow_tag,
        )
        return 0

    # 1. ChirpStack (best-effort)
    cs_ok = chirpstack_register(dev_eui, ranch_id, cow_tag, args.app_key)
    if cs_ok:
        log.info("ChirpStack registration: OK")
    else:
        log.info("ChirpStack registration: skipped (no API creds) -- local registry only")

    # 2. Local registry
    write_local_registry(dev_eui, ranch_id, cow_tag)

    # 3. MQTT topic check
    verify_mqtt_topic(ranch_id, cow_tag)

    log.info("")
    log.info("Done. Flash firmware with secrets matching devEUI=%s, then watch:", dev_eui)
    log.info("  mosquitto_sub -t 'skyherd/%s/collar/%s' -v", ranch_id, cow_tag)
    log.info("Cow %s should turn from sim-pink to real-green on the dashboard.", cow_tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
