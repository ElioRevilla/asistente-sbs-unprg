from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Student:
    """Student using the SBS assistant."""

    id: UUID | None
    name: str | None
    email: str
    created_at: datetime | None = None
