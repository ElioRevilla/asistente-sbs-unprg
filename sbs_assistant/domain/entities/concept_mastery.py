from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConceptMastery:
    """Student mastery state for a regulatory concept."""

    student_id: UUID
    concept: str
    mastery_score: float = 0.5
    attempts: int = 0
    last_activity: datetime | None = None
