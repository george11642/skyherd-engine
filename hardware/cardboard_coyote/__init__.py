"""Cardboard-coyote thermal harness — thin re-export of :mod:`skyherd.edge.coyote_harness`.

The real implementation lives at ``src/skyherd/edge/coyote_harness.py``.
This shim exists because ``docs/HARDWARE_H1_RUNBOOK.md`` documents the
canonical hardware-dir import path for judges browsing the tree.
"""

from skyherd.edge.coyote_harness import CoyoteHarness

__all__ = ["CoyoteHarness"]
