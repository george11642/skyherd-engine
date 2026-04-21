"""DetectionResult — output of a single disease-detection head."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["watch", "log", "escalate", "vet_now"]


class DetectionResult(BaseModel):
    """Pydantic model returned by each disease-detection head."""

    head_name: str
    cow_tag: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    reasoning: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
