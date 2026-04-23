"""Centralized Twilio auth-token lookup for SkyHerd voice + MCP modules.

Prefers the canonical ``TWILIO_AUTH_TOKEN`` environment variable and falls back
to the legacy ``TWILIO_TOKEN`` with a one-shot ``DeprecationWarning``.  Rename
intent: standardize on the name Twilio itself uses (AUTH_TOKEN) so operators
setting one variable no longer see silent voice-call failures on the other path.
Future removal: ``TWILIO_TOKEN`` support will be dropped once all deployments
have migrated; the ``_DEPRECATION_EMITTED`` cache ensures the warning surfaces
exactly once per process without flooding logs.
"""
from __future__ import annotations

import os
import warnings

# Module-level cache: once "TWILIO_TOKEN" is inserted here the DeprecationWarning
# will not be emitted again for the lifetime of the current Python process.
_DEPRECATION_EMITTED: set[str] = set()

_LEGACY_KEY = "TWILIO_TOKEN"
_CANONICAL_KEY = "TWILIO_AUTH_TOKEN"
_DEPRECATION_MESSAGE = (
    "TWILIO_TOKEN env var is deprecated; rename to TWILIO_AUTH_TOKEN. "
    "TWILIO_TOKEN will be removed in a future release."
)


def _get_twilio_auth_token() -> str:
    """Return the Twilio auth token from the environment.

    Lookup order:
    1. ``TWILIO_AUTH_TOKEN`` — canonical name; returned immediately if truthy.
    2. ``TWILIO_TOKEN`` — legacy fallback; accepted but emits a
       ``DeprecationWarning`` once per process (via ``_DEPRECATION_EMITTED``
       cache) with ``stacklevel=2`` so the warning points at the caller.
    3. Empty string — if neither variable is set.

    Security: this function never logs or warns with the token *value*.  The
    warning message is a static constant string; the token is only returned as
    the function's return value.
    """
    canonical = os.environ.get(_CANONICAL_KEY, "")
    if canonical:
        return canonical

    legacy = os.environ.get(_LEGACY_KEY, "")
    if legacy and _LEGACY_KEY not in _DEPRECATION_EMITTED:
        _DEPRECATION_EMITTED.add(_LEGACY_KEY)
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)

    return legacy
