"""structlog configuration for SkyHerd.

Call ``configure()`` once at process start (before any logging calls).

Format selection
----------------
- ``SKYHERD_LOG_FORMAT=json``  — JSON lines (default in production)
- ``SKYHERD_LOG_FORMAT=text``  — human-readable coloured console (default in dev)

If structlog is not installed, falls back to stdlib logging transparently.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

_CONFIGURED = False


def configure(fmt: str | None = None) -> None:
    """Configure structlog + stdlib logging.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    log_format = fmt or os.environ.get("SKYHERD_LOG_FORMAT", "json")

    try:
        import structlog

        shared_processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
        ]

        if log_format == "text":
            renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
        else:
            renderer = structlog.processors.JSONRenderer()

        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    except ImportError:
        # structlog not installed — fall back to stdlib with a simple format
        _fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=_fmt,
            stream=sys.stdout,
        )


def get_logger(name: str = "skyherd") -> Any:
    """Return a structlog logger (or stdlib logger if structlog missing)."""
    try:
        import structlog

        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)
