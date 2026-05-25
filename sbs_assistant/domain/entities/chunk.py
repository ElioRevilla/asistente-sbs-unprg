from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Chunk:
    """Regulatory chunk with retrieval metadata."""

    id: str
    text: str
    chapter: str | None = None
    article: int | None = None
    numeral: str | None = None
    content_type: str | None = None
    topics: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    created_at: datetime | None = None
