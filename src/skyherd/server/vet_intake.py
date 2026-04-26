"""Vet intake drafter (SCEN-01 + DASH-06).

Writes rancher-readable markdown packets for HerdHealthWatcher escalations.
Schema sourced from RESEARCH.md Pattern 5 + skills/cattle-behavior/disease/pinkeye.md.

DASH-06: signals_structured carries Phase 2 VIS-05 DetectionResult.bbox from the
pinkeye pixel head through to the front-end, where Plan 05-03's VetIntakePanel
renders it as a bounding-box detection chip.

Path-traversal guard: cow_tag must match ^[A-Z][0-9]{3}$ and the resolved file
path must start with the resolved intake dir (Pitfall 5).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VET_INTAKE_DIR = Path("runtime/vet_intake")

# Cow tag format: one uppercase letter followed by exactly three digits (e.g. A014)
_COW_TAG_RE = re.compile(r"^[A-Z][0-9]{3}$")

# Intake ID format: <tag>_<yyyymmdd>T<hhmmss>Z (used for retrieval validation)
_INTAKE_ID_RE = re.compile(r"^[A-Z][0-9]{3}_[0-9]{8}T[0-9]{6}Z$")

# Disease-specific treatment guidance (sourced from skills/cattle-behavior/disease/pinkeye.md)
_TREATMENT_GUIDANCE: dict[str, list[str]] = {
    "pinkeye": [
        "200 mg oxytetracycline LA IM (single dose — most effective within first 24h).",
        "Patch affected eye to reduce UV exposure and fly contact.",
        "Isolate from bright sunlight; move to shaded area if possible.",
        "Bilateral or unresponsive after 5 days → vet evaluation (subconjunctival penicillin).",
        "Monitor BCS — blind animals cannot graze efficiently; provide feed access.",
    ],
    "screwworm": [
        "Remove maggots mechanically; apply approved insecticide spray.",
        "Immediate vet evaluation — reportable disease in many states.",
        "Isolate animal; prevent fly access to wound.",
    ],
    "foot_rot": [
        "Clean wound; apply zinc sulfate foot bath.",
        "200 mg oxytetracycline LA IM or trimethoprim/sulfa orally per label.",
        "Hoof trim if severe; vet evaluation if limb swelling above fetlock.",
    ],
    "brd": [
        "Immediate antimicrobial therapy (florfenicol or tulathromycin per label dose).",
        "NSAIDs (flunixin meglumine) for fever and inflammation.",
        "Isolate from herd; reduce stress; ensure water access.",
        "Vet evaluation if no improvement within 48h.",
    ],
}

_DEFAULT_TREATMENT = [
    "Rancher to inspect animal within 2 hours.",
    "Contact vet if condition worsens or fails to improve within 24h.",
]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class VetIntakeRecord(BaseModel):
    """Rancher-readable vet intake packet produced by draft_vet_intake()."""

    id: str
    cow_tag: str
    severity: str  # "log" | "observe" | "escalate"
    disease: str
    ts_iso: str
    path: str  # Absolute path to the .md artifact on disk
    drafted_by: str
    signals_structured: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def draft_vet_intake(
    cow_tag: str,
    severity: str,
    disease: str,
    signals: list[str],
    cow_snapshot: dict[str, Any],
    session_id: str,
    herd_context: str,
    attest_seq: int | None = None,
    signals_structured: list[dict[str, Any]] | None = None,
) -> VetIntakeRecord:
    """Write a rancher-readable markdown vet-intake packet to runtime/vet_intake/.

    Args:
        cow_tag: Cattle tag — must match ^[A-Z][0-9]{3}$ (e.g. "A014").
        severity: One of "log", "observe", "escalate".
        disease: Primary disease flag (e.g. "pinkeye").
        signals: Human-readable signal strings (e.g. ["ocular_discharge=0.70"]).
        cow_snapshot: Dict with at least "tag", "bcs", "health_score".
        session_id: Agent session ID for traceability.
        herd_context: Free-form herd context string.
        attest_seq: Optional attestation ledger sequence number.
        signals_structured: Optional list of structured signal dicts. DASH-06:
            when Phase 2 VIS-05 pixel head fires, caller injects:
            {"kind": "pixel_detection", "head": "pinkeye",
             "bbox": [x0, y0, x1, y1], "confidence": 0.87}

    Returns:
        VetIntakeRecord with the absolute path to the .md file.

    Raises:
        ValueError: If cow_tag fails regex validation or path traversal detected.
    """
    # 1. Validate cow_tag
    if not _COW_TAG_RE.match(cow_tag):
        raise ValueError(f"cow_tag {cow_tag!r} does not match required regex ^[A-Z][0-9]{{3}}$")

    # 2. Build timestamp and intake ID
    ts = datetime.now(UTC)
    ts_compact = ts.strftime("%Y%m%dT%H%M%SZ")
    intake_id = f"{cow_tag}_{ts_compact}"
    filename = f"{intake_id}.md"

    # 3. Create intake directory
    _VET_INTAKE_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Path-traversal guard: resolve + assert containment
    candidate = (_VET_INTAKE_DIR / filename).resolve()
    intake_dir_resolved = _VET_INTAKE_DIR.resolve()
    if not str(candidate).startswith(str(intake_dir_resolved)):
        raise ValueError(
            f"Path traversal attempt detected: {candidate} is outside {intake_dir_resolved}"
        )

    # 5. Normalise signals_structured
    structured: list[dict[str, Any]] = signals_structured or []

    # 6. Render markdown
    body = _render_markdown(
        intake_id=intake_id,
        cow_tag=cow_tag,
        severity=severity,
        disease=disease,
        signals=signals,
        cow_snapshot=cow_snapshot,
        session_id=session_id,
        herd_context=herd_context,
        ts=ts,
        attest_seq=attest_seq,
        signals_structured=structured,
    )

    # 7. Write to disk
    candidate.write_text(body, encoding="utf-8")
    logger.info("Vet intake drafted: %s", candidate)

    return VetIntakeRecord(
        id=intake_id,
        cow_tag=cow_tag,
        severity=severity,
        disease=disease,
        ts_iso=ts.isoformat(),
        path=str(candidate),
        drafted_by=f"HerdHealthWatcher (session {session_id})",
        signals_structured=structured,
    )


def get_intake_path(intake_id: str) -> Path:
    """Return the Path for a given intake_id.

    Validates that *intake_id* matches the canonical pattern
    ``^[A-Z][0-9]{3}_[0-9]{8}T[0-9]{6}Z$`` (e.g. ``A014_20260101T000000Z``)
    before returning the resolved path. This is the regex-guard referenced
    by the HTTP endpoint in Plan 05-03; callers that catch ``ValueError``
    return 400 to the client.

    Uses ``_VET_INTAKE_DIR`` so monkeypatching works in tests.
    """
    if not _INTAKE_ID_RE.match(intake_id):
        raise ValueError(
            f"intake_id {intake_id!r} does not match required regex "
            r"^[A-Z][0-9]{3}_[0-9]{8}T[0-9]{6}Z$"
        )

    # Path-traversal guard: the intake_id regex already rules out "/" and "..",
    # but resolve + startswith gives us defense in depth.
    candidate = (_VET_INTAKE_DIR / f"{intake_id}.md").resolve()
    intake_dir_resolved = _VET_INTAKE_DIR.resolve()
    if not str(candidate).startswith(str(intake_dir_resolved)):
        raise ValueError(
            f"Path traversal attempt detected: {candidate} outside {intake_dir_resolved}"
        )
    # Return the un-resolved path (tests monkeypatch _VET_INTAKE_DIR to tmp_path;
    # resolving at call time would lock-in a different base directory if the
    # caller monkeypatches mid-test).
    return _VET_INTAKE_DIR / f"{intake_id}.md"


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def _render_markdown(
    intake_id: str,
    cow_tag: str,
    severity: str,
    disease: str,
    signals: list[str],
    cow_snapshot: dict[str, Any],
    session_id: str,
    herd_context: str,
    ts: datetime,
    attest_seq: int | None,
    signals_structured: list[dict[str, Any]],
) -> str:
    """Render a rancher-readable markdown packet (Pattern 5 from RESEARCH.md)."""
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    severity_display = severity.upper()
    disease_display = disease.replace("_", " ").title()

    bcs = cow_snapshot.get("bcs", "N/A")
    health_score = cow_snapshot.get("health_score", "N/A")

    # Signals bullet list
    signals_md = "\n".join(f"- {s}" for s in signals) if signals else "- (none recorded)"

    # Treatment guidance
    treatment_list = _TREATMENT_GUIDANCE.get(disease, _DEFAULT_TREATMENT)
    treatment_md = "\n".join(f"- {t}" for t in treatment_list)

    # Structured Signals section (DASH-06) — present only when non-empty
    structured_section = ""
    if signals_structured:
        lines = ["## Structured Signals (DASH-06)", ""]
        for sig in signals_structured:
            kind = sig.get("kind", "unknown")
            head = sig.get("head", "")
            bbox = sig.get("bbox")
            confidence = sig.get("confidence")
            # Render bbox as [x0, y0, x1, y1] literal so test regex matches
            bbox_str = f" bbox={list(bbox)}" if bbox is not None else ""
            conf_str = f" conf={float(confidence):.2f}" if confidence is not None else ""
            lines.append(f"- kind={kind} head={head}{bbox_str}{conf_str}")
        structured_section = "\n".join(lines) + "\n\n"

    attest_str = f"- Event seq: {attest_seq}" if attest_seq is not None else "- (not yet recorded)"

    return (
        f"# Vet Intake — {cow_tag} · {disease_display} · {severity_display}\n\n"
        f"**Drafted:** {ts_str}\n"
        f"**Drafted by:** HerdHealthWatcher (session {session_id})\n\n"
        f"## Cow\n"
        f"- Tag: {cow_tag}\n"
        f"- BCS: {bcs} · Health score: {health_score}\n\n"
        f"## Finding\n"
        f"- Disease: {disease_display}\n"
        f"- Severity: {severity_display}\n"
        f"- Signals:\n{signals_md}\n\n"
        f"{structured_section}"
        f"## Recommended Next Action\n"
        f"{treatment_md}\n\n"
        f"## Herd Context\n"
        f"- {herd_context}\n\n"
        f"## Attestation\n"
        f"{attest_str}\n\n"
        f"*This document was drafted by HerdHealthWatcher. It is not a veterinary diagnosis.*\n"
    )
