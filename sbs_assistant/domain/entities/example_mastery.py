from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ExampleMastery:
    """Adaptive practice state for Ejemplifica."""

    student_key: str
    concept: str
    mastery_score: float = 0.5
    attempts: int = 0
    last_answer_correct: bool | None = None
    updated_at: datetime | None = None
