"""Thin re-export of :mod:`skyherd.edge.coyote_harness`.

Kept for judge-friendly ``from hardware.cardboard_coyote.coyote_harness import
CoyoteHarness`` invocations referenced in the Phase 5 runbook.

Implementation lives at ``src/skyherd/edge/coyote_harness.py``.
"""

from skyherd.edge.coyote_harness import (
    CoyoteHarness,
    _canonical_json,
    _parse_mqtt_url,
)

__all__ = ["CoyoteHarness", "_canonical_json", "_parse_mqtt_url"]
