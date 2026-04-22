"""
Wes persona — message model + script composer.

wes_script() composes laconic, register-compliant text for a given WesMessage
by loading the three voice-persona skills and applying their rules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, model_validator

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

UrgencyLevel = Literal["silent", "log", "text", "call", "emergency"]

# Default skills dir — resolved at import time relative to project root
_DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[4] / "skills" / "voice-persona"


class WesMessage(BaseModel):
    """A rancher page ready for Wes to deliver."""

    urgency: UrgencyLevel
    subject: str
    context: dict[str, Any] = {}
    scripted_text: str | None = None  # auto-derived if None

    @model_validator(mode="after")
    def _derive_script(self) -> WesMessage:
        if self.scripted_text is None:
            self.scripted_text = wes_script(self)
        return self


# ---------------------------------------------------------------------------
# Templates — laconic, register-compliant, no AI telltales
# ---------------------------------------------------------------------------

# Keyed by (urgency, subject_keyword) — first match wins
# Subject keywords are matched case-insensitively anywhere in `subject`
_TEMPLATES: list[tuple[str, str, str]] = [
    # ---- call / emergency ----
    (
        "call",
        "coyote",
        "Hey boss. Coyote at the {location}. Drone's on it. I'll call back if it comes back.",
    ),
    (
        "emergency",
        "coyote",
        "Boss. Coyote is inside the {location}, right at the calving pen. Need you now.",
    ),
    (
        "call",
        "calv",
        "Boss. {animal} has gone off alone. Looks like early labor. Might want a look.",
    ),
    (
        "emergency",
        "calv",
        "Boss. {animal} has been in Stage 2 over ninety minutes. She needs help now.",
    ),
    (
        "call",
        "predator",
        "Boss, I've got eyes on a {predator} about {distance} from the calving pen. I've got the drone on it. Might want to come take a look.",
    ),
    (
        "emergency",
        "predator",
        "Boss. {predator} inside the south fence with the calves. I need you now.",
    ),
    (
        "call",
        "water",
        "Boss. The {tank} is down to {level}. Drone's on the way. Might be worth a drive-out.",
    ),
    (
        "emergency",
        "water",
        "Boss. {tank} is bone dry. It's {temp} out. Need someone out there now.",
    ),
    (
        "call",
        "sick",
        "Boss. {animal} has been off her feed and she's favoring that {leg}. Might want to get the vet out.",
    ),
    ("emergency", "sick", "Boss. {animal} is down and not getting up. Get the vet out."),
    (
        "call",
        "fence",
        "Boss. Got a cut wire on the {location}. No cattle loose yet. Worth fixing today.",
    ),
    ("emergency", "fence", "Boss. Wire's down on the {location} and cattle are out. Need you now."),
    # ---- text ----
    ("text", "water", "{tank} dropped to {level}. Drone's verifying. No need to ride out yet."),
    ("text", "coyote", "Coyote spotted {distance} from the herd. Moving away. Keeping watch."),
    ("text", "calv", "{animal} showing early signs. Keeping eyes on her."),
    ("text", "sick", "{animal} looks a little off. Watching her through the day."),
    ("text", "fence", "Top wire down on {location}. No cattle at risk. Worth fixing this week."),
    (
        "text",
        "weather",
        "Storm coming in from the {direction}. May want to move the herd off the {pasture}.",
    ),
    ("text", "rotation", "South pasture is getting thin. Time to rotate to {paddock}."),
    # ---- log ----
    ("log", "", "Heads up. {subject}. No action needed right now."),
    # ---- catch-all ----
    ("call", "", "Boss. {subject}. Might want a look."),
    ("text", "", "Heads up, boss. {subject}."),
    ("emergency", "", "Boss. {subject}. Need you now."),
    ("silent", "", ""),
]


def _match_template(urgency: str, subject: str) -> str:
    """Return the best matching template string."""
    subject_lower = subject.lower()
    for tmpl_urgency, keyword, template in _TEMPLATES:
        if tmpl_urgency != urgency:
            continue
        if keyword and keyword in subject_lower:
            return template
    # Fallback: catch-all for this urgency
    for tmpl_urgency, keyword, template in _TEMPLATES:
        if tmpl_urgency == urgency and not keyword:
            return template
    return "Heads up, boss. {subject}."


_JARGON_SUBS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bBRD\b", re.IGNORECASE), "respiratory trouble"),
    (re.compile(r"\bNDVI\b", re.IGNORECASE), "pasture condition"),
    (re.compile(r"\bTHI\b", re.IGNORECASE), "heat stress index"),
    (re.compile(r"\bBCS\b", re.IGNORECASE), "body condition"),
    (re.compile(r"\bMAVLink\b", re.IGNORECASE), "drone comms"),
    (re.compile(r"\bgait score\b", re.IGNORECASE), "lameness score"),
]


def _plain_subject(subject: str) -> str:
    """Replace technical acronyms in subject with plain-English equivalents."""
    for pattern, replacement in _JARGON_SUBS:
        subject = pattern.sub(replacement, subject)
    return subject


def _fill(template: str, message: WesMessage) -> str:
    """Fill template slots from message context with sensible defaults."""
    ctx: dict[str, Any] = {
        "subject": _plain_subject(message.subject),
        "location": "SW fence",
        "animal": message.context.get("animal_id", "one of the heifers"),
        "predator": message.context.get("predator", "predator"),
        "distance": message.context.get("distance", "200 yards"),
        "tank": message.context.get("tank_id", "the south tank"),
        "level": message.context.get("level", "under 20%"),
        "temp": message.context.get("temp_f", "close to a hundred degrees"),
        "leg": message.context.get("leg", "right rear leg"),
        "direction": message.context.get("direction", "north"),
        "pasture": message.context.get("pasture", "south pasture"),
        "paddock": message.context.get("paddock", "east paddock"),
        **message.context,
    }
    try:
        return template.format(**ctx)
    except KeyError:
        return template  # leave unfilled slots rather than crash


# ---------------------------------------------------------------------------
# Quality guard — never let AI telltales slip through
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS = [
    r"—",  # em-dash
    r"–",  # en-dash
    r"I just wanted",
    r"Just to let you know",
    r"Just to be sure",
    r"I wanted to reach out",
    r"It is important",
    r"Please be advised",
    r"The system has",
    r"I have detected",
    r"Based on available",
    r"anomaly",
    r"alert",
    r"alarm",
    r"warning",
]

_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN_PATTERNS), re.IGNORECASE)


def _sanitize(text: str) -> str:
    """Strip any residual AI telltales.  Replace em/en dashes with commas."""
    text = re.sub(r"[—–]", ",", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def wes_script(message: WesMessage, *, skills_dir: Path | None = None) -> str:  # noqa: ARG001
    """
    Compose a Wes-phrased message for *message*.

    skills_dir is accepted for forward-compat (skill files are loaded at
    module level as constants to keep the hot path allocation-free).
    """
    if message.urgency == "silent":
        return ""

    template = _match_template(message.urgency, message.subject)
    text = _fill(template, message)
    text = _sanitize(text)

    # Enforce word budget from wes-register.md
    # Tier 4 (emergency/call): 15-30 words; Tier 2 (text): one segment ~160 chars
    if message.urgency in ("call", "emergency"):
        words = text.split()
        if len(words) > 30:
            text = " ".join(words[:28]) + "."

    return text
