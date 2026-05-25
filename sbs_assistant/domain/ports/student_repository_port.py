from typing import Protocol
from uuid import UUID

from sbs_assistant.domain.entities.student import Student


class StudentRepositoryPort(Protocol):
    """Persistence port for students."""

    async def get(self, student_id: UUID) -> Student | None:
        """Return a student by id."""
