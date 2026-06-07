from typing import Protocol

from sbs_assistant.domain.entities.example_mastery import ExampleMastery


class ExampleMasteryRepositoryPort(Protocol):
    """Persistence port for adaptive Ejemplifica mastery."""

    async def get(self, student_key: str, concept: str) -> ExampleMastery | None:
        """Return the mastery state for one concept."""

    async def list_by_student(self, student_key: str) -> list[ExampleMastery]:
        """Return all tracked concepts for one student."""

    async def upsert(
        self,
        mastery: ExampleMastery,
    ) -> ExampleMastery:
        """Create or update a mastery record."""
