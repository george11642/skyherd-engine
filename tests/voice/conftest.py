"""Shared pytest fixtures for tests/voice/.

Includes an autouse fixture that clears the _DEPRECATION_EMITTED cache between
tests.  This cache is a module-level set used by _get_twilio_auth_token() to
guarantee that the DeprecationWarning for the legacy TWILIO_TOKEN env var is
emitted at most once per process.  Without clearing it between tests, a test
that exercises the legacy path first would suppress the warning for all
subsequent tests in the same process — causing false negatives in any test
that asserts the warning IS emitted.  Clearing before and after each test
restores the per-test isolation guarantee without changing production behavior
(production has a single long-lived process, so once-per-process remains true).

Also includes an autouse ``default_voice_mock`` fixture that sets
``SKYHERD_VOICE=mock`` by default for every voice test, forcing SilentBackend
and skipping Twilio.  Tests that need live-chain behavior override with
``monkeypatch.setenv("SKYHERD_VOICE", "live")`` in their own body — this works
because pytest's ``monkeypatch`` acts on the live ``os.environ`` dict, so a
later setenv overrides the earlier one, and the fixture's teardown still
reverts the environment at the end of the test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def default_voice_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default SKYHERD_VOICE=mock for every voice test; tests override as needed."""
    monkeypatch.setenv("SKYHERD_VOICE", "mock")


@pytest.fixture(autouse=True)
def reset_twilio_deprecation_cache() -> None:
    """Clear the once-per-process DeprecationWarning cache before and after each test.

    The _DEPRECATION_EMITTED set in skyherd.voice._twilio_env tracks whether the
    TWILIO_TOKEN deprecation warning has been emitted.  Resetting it here ensures
    tests run in isolation regardless of execution order.
    """
    # Lazy import so collection succeeds even before the module is created
    # (during TDD RED phase the module does not yet exist, but autouse fixtures
    # are collected at test-session start for all test modules in tests/voice/).
    # We guard the import so that tests unrelated to _twilio_env still run.
    try:
        from skyherd.voice._twilio_env import _DEPRECATION_EMITTED

        _DEPRECATION_EMITTED.clear()
    except ImportError:
        pass

    yield

    try:
        from skyherd.voice._twilio_env import _DEPRECATION_EMITTED

        _DEPRECATION_EMITTED.clear()
    except ImportError:
        pass
