"""Tests for wes_script composition — persona, register, urgency mapping."""

from __future__ import annotations

import re

import pytest

from skyherd.voice.wes import WesMessage, _sanitize, wes_script

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TELLTALE_RE = re.compile(
    r"—|–|I just wanted|Just to let you know|Just to be sure"
    r"|I wanted to reach out|It is important|Please be advised"
    r"|The system has|I have detected|Based on available",
    re.IGNORECASE,
)


def _make(urgency: str, subject: str, **ctx) -> WesMessage:
    return WesMessage(urgency=urgency, subject=subject, context=ctx)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Urgency mapping
# ---------------------------------------------------------------------------


def test_silent_returns_empty():
    msg = _make("silent", "routine patrol")
    assert wes_script(msg) == ""


def test_log_returns_non_empty():
    msg = _make("log", "battery swap complete")
    assert wes_script(msg).strip() != ""


def test_call_urgency_short():
    """Call scripts must fit ElevenLabs voice budget (<=30 words)."""
    msg = _make("call", "coyote at the SW fence", location="SW fence")
    script = wes_script(msg)
    assert len(script.split()) <= 30


def test_emergency_urgency_very_short():
    """Emergency scripts must be terse (<= 30 words; ideally <25)."""
    msg = _make("emergency", "coyote inside perimeter", location="south fence")
    script = wes_script(msg)
    assert len(script.split()) <= 30


def test_text_urgency_fits_sms():
    """Text-tier scripts should fit one SMS segment (<=160 chars)."""
    msg = _make("text", "water tank 3 low", tank_id="Tank 3", level="18%")
    script = wes_script(msg)
    assert len(script) <= 160


# ---------------------------------------------------------------------------
# Register compliance
# ---------------------------------------------------------------------------


def test_no_em_dash(monkeypatch):
    """em-dash must never appear in any generated script."""
    for urgency in ("log", "text", "call", "emergency"):
        msg = _make(urgency, "fence wire down")
        script = wes_script(msg)
        assert "—" not in script, f"em-dash found in {urgency!r} script: {script!r}"


def test_no_en_dash():
    for urgency in ("log", "text", "call", "emergency"):
        msg = _make(urgency, "sick cow")
        script = wes_script(msg)
        assert "–" not in script


def test_no_ai_telltales():
    """Generic AI phrases must not appear in any generated script."""
    subjects = [
        ("call", "coyote spotted"),
        ("text", "water tank pressure drop"),
        ("call", "calving detected"),
        ("emergency", "predator inside herd"),
        ("text", "fence line anomaly"),
    ]
    for urgency, subject in subjects:
        msg = _make(urgency, subject)
        script = wes_script(msg)
        match = _TELLTALE_RE.search(script)
        assert match is None, (
            f"Telltale {match.group()!r} found in {urgency!r}/{subject!r}: {script!r}"
        )


def test_no_system_jargon():
    """Technical system jargon must be absent or translated."""
    jargon_patterns = re.compile(
        r"\bMAVLink\b|\bBRD\b|\bNDVI\b|\bTHI\b|\bgait score\b", re.IGNORECASE
    )
    msg = _make("call", "BRD suspected in cow B007", animal_id="B007")
    script = wes_script(msg)
    assert not jargon_patterns.search(script), f"Jargon found: {script!r}"


# ---------------------------------------------------------------------------
# Auto-derivation via model_validator
# ---------------------------------------------------------------------------


def test_model_auto_derives_script():
    """WesMessage without scripted_text should auto-derive it."""
    msg = WesMessage(urgency="call", subject="coyote at the fence")
    assert msg.scripted_text is not None
    assert len(msg.scripted_text) > 0


def test_model_respects_provided_script():
    """WesMessage with explicit scripted_text should not overwrite it."""
    custom = "Hey boss. Just checking in. All's quiet."
    msg = WesMessage(urgency="log", subject="nothing", scripted_text=custom)
    assert msg.scripted_text == custom


# ---------------------------------------------------------------------------
# Specific scenario scripts (regression)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "urgency,subject,ctx_key,ctx_val,expected_fragment",
    [
        ("call", "coyote at the SW fence", "location", "SW fence", "boss"),
        ("call", "calving detected — B007", "animal_id", "B007", "boss"),
        ("text", "water tank low", "tank_id", "Tank 3", "Tank 3"),
    ],
)
def test_scenario_scripts(urgency, subject, ctx_key, ctx_val, expected_fragment):
    msg = _make(urgency, subject, **{ctx_key: ctx_val})
    script = wes_script(msg)
    assert expected_fragment.lower() in script.lower(), (
        f"Fragment {expected_fragment!r} missing from: {script!r}"
    )


# ---------------------------------------------------------------------------
# C3 regression — _sanitize() is invoked on every output path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "injected_phrase,description",
    [
        ("I just wanted to let you know", "AI soft opener"),
        ("Just to let you know,", "AI soft opener variant"),
        ("I have detected an anomaly", "AI detection language"),
        ("Based on available data,", "AI hedge phrase"),
        ("The system has flagged", "AI system language"),
        ("Please be advised that", "AI corporate opener"),
        ("It is important to note", "AI hedge"),
        ("I wanted to reach out because", "AI reach-out"),
        ("anomaly detected in sector 4", "AI anomaly phrase"),
        ("anomaly identified near fence", "AI anomaly phrase 2"),
        ("em—dash test", "em-dash"),
        ("en–dash test", "en-dash"),
    ],
)
def test_sanitize_strips_ai_telltales(injected_phrase: str, description: str) -> None:
    """_sanitize() must rewrite or remove every known AI telltale phrase."""
    result = _sanitize(injected_phrase)
    # The original phrase should not survive intact (case-insensitive)
    assert injected_phrase.lower() not in result.lower(), (
        f"AI telltale ({description}) survived _sanitize(): {result!r}"
    )
    # em/en dashes must not appear in the output
    assert "—" not in result and "–" not in result, f"Dash survived sanitize in: {result!r}"


def test_wes_script_sanitizes_injected_em_dash() -> None:
    """wes_script() output must never contain an em-dash even if subject contains one."""
    msg = WesMessage(urgency="call", subject="fence—breached near calving pen")
    script = wes_script(msg)
    assert "—" not in script, f"em-dash in wes_script output: {script!r}"


def test_wes_script_sanitizes_injected_ai_opener() -> None:
    """wes_script() output must not pass through AI opener phrases from subject."""
    msg = WesMessage(
        urgency="call",
        subject="I just wanted to let you know about the coyote",
    )
    script = wes_script(msg)
    assert "i just wanted" not in script.lower(), f"AI opener survived wes_script(): {script!r}"
