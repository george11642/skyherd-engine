"""
Humanize regression tests — generated scripts must pass a no-AI-telltale
and no-em-dash regex check across all urgency levels and scenario types.
"""

from __future__ import annotations

import re

import pytest

from skyherd.voice.wes import WesMessage, wes_script

# ---------------------------------------------------------------------------
# Patterns that must NEVER appear in a Wes script
# ---------------------------------------------------------------------------

_BANNED_EXACT = [
    # em/en dashes
    "—",
    "–",
    # classic AI padding stems
    "I just wanted",
    "Just to let you know",
    "Just to be sure",
    "I wanted to reach out",
    "It is important",
    "Please be advised",
    "The system has",
    "I have detected",
    "Based on available",
    "anomaly",
    "alert",
    "alarm",
]

_BANNED_RE = re.compile("|".join(re.escape(p) for p in _BANNED_EXACT), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Fixtures: (urgency, subject, context)
# ---------------------------------------------------------------------------

_SCENARIOS = [
    ("call", "coyote at the SW fence", {"location": "SW fence"}),
    ("emergency", "coyote inside calving pen", {"location": "south fence"}),
    ("call", "calving detected B007", {"animal_id": "B007"}),
    ("emergency", "calving dystocia stage 2", {"animal_id": "B012"}),
    ("text", "water tank 3 low", {"tank_id": "Tank 3", "level": "18%"}),
    ("text", "fence top wire down", {"location": "north pasture"}),
    ("call", "sick cow favoring leg", {"animal_id": "C021", "leg": "left front leg"}),
    ("log", "LGD patrol complete", {}),
    ("text", "paddock rotation due", {"paddock": "east paddock"}),
    ("call", "predator spotted near herd", {"predator": "mountain lion", "distance": "300 yards"}),
    (
        "emergency",
        "water dry in summer heat",
        {"tank_id": "south tank", "temp_f": "close to a hundred"},
    ),
]


@pytest.mark.parametrize("urgency,subject,ctx", _SCENARIOS)
def test_no_banned_patterns(urgency, subject, ctx):
    msg = WesMessage(urgency=urgency, subject=subject, context=ctx)  # type: ignore[arg-type]
    script = wes_script(msg)
    match = _BANNED_RE.search(script)
    assert match is None, (
        f"Banned pattern {match.group()!r} found in script for "
        f"urgency={urgency!r}, subject={subject!r}:\n  {script!r}"
    )


@pytest.mark.parametrize("urgency,subject,ctx", _SCENARIOS)
def test_starts_with_lowercase_or_boss(urgency, subject, ctx):
    """Scripts should not start with robot-style sentence framing."""
    if urgency == "silent":
        return
    msg = WesMessage(urgency=urgency, subject=subject, context=ctx)  # type: ignore[arg-type]
    script = wes_script(msg)
    # Must not start with 'System', 'Alert', 'Warning', 'Notice', 'Notification'
    bad_starts = re.compile(r"^(system|alert|warning|notice|notification)", re.IGNORECASE)
    assert not bad_starts.match(script), f"Robot start in: {script!r}"


@pytest.mark.parametrize("urgency,subject,ctx", _SCENARIOS)
def test_no_exclamation_in_call_scripts(urgency, subject, ctx):
    """Voice scripts must never use exclamation marks."""
    if urgency not in ("call", "emergency"):
        return
    msg = WesMessage(urgency=urgency, subject=subject, context=ctx)  # type: ignore[arg-type]
    script = wes_script(msg)
    assert "!" not in script, f"Exclamation found in voice script: {script!r}"
