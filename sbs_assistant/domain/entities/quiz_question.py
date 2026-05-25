from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    """Curated or generated quiz question."""

    id: UUID | None
    concept: str
    question_type: str
    difficulty: float
    bloom_level: str | None
    prompt: str
    options: dict[str, str] | None
    correct_answer: str
    explanation: str
    source_article: str
    curated_by_human: bool = False
