"""Tests for the _twilio_env helper module (HYG-02).

Verifies:
- TWILIO_AUTH_TOKEN is preferred over legacy TWILIO_TOKEN
- Legacy TWILIO_TOKEN emits DeprecationWarning exactly once per process
- Once-per-process cache prevents repeated warnings
- Neither var set returns empty string, no warning
"""
from __future__ import annotations

import warnings

import pytest

from skyherd.voice._twilio_env import _get_twilio_auth_token


class TestGetTwilioAuthToken:
    def test_auth_token_reads_new_var(self, monkeypatch):
        """TWILIO_AUTH_TOKEN is returned without any DeprecationWarning."""
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "new_value")
        monkeypatch.delenv("TWILIO_TOKEN", raising=False)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _get_twilio_auth_token()

        assert result == "new_value"
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert deprecation_warnings == [], "No DeprecationWarning expected when TWILIO_AUTH_TOKEN is set"

    def test_legacy_token_emits_deprecation(self, monkeypatch):
        """Legacy TWILIO_TOKEN is accepted but emits DeprecationWarning."""
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.setenv("TWILIO_TOKEN", "legacy")

        with pytest.warns(DeprecationWarning, match="TWILIO_TOKEN"):
            result = _get_twilio_auth_token()

        assert result == "legacy"

    def test_deprecation_warning_emitted_once(self, monkeypatch):
        """Once-per-process cache: second call emits zero new warnings."""
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.setenv("TWILIO_TOKEN", "legacy")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)
            # First call — should emit one warning
            result1 = _get_twilio_auth_token()
            count_after_first = len([x for x in w if issubclass(x.category, DeprecationWarning)])
            # Second call — should NOT emit another warning (cache hit)
            result2 = _get_twilio_auth_token()
            count_after_second = len([x for x in w if issubclass(x.category, DeprecationWarning)])

        assert result1 == "legacy"
        assert result2 == "legacy"
        assert count_after_first == 1, "First call must emit exactly 1 DeprecationWarning"
        assert count_after_second == 1, "Second call must NOT emit a new DeprecationWarning"

    def test_neither_var_returns_empty(self, monkeypatch):
        """Neither var set → empty string, no warning emitted."""
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_TOKEN", raising=False)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _get_twilio_auth_token()

        assert result == ""
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert deprecation_warnings == [], "No DeprecationWarning expected when neither var is set"
