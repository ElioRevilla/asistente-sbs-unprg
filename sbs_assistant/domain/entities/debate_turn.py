from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DebateTurn:
    """A single turn in an adversarial simulation transcript."""

    role: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime | None = None
