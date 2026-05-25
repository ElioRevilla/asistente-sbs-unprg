from typing import Protocol
from uuid import UUID

from sbs_assistant.domain.entities.case import SyntheticCase


class SyntheticCaseRepositoryPort(Protocol):
    """Persistence port for generated synthetic debtor cases."""

    async def save(self, case: SyntheticCase) -> SyntheticCase:
        """Persist a synthetic case and return it with its generated ID."""

    async def get(self, case_id: UUID) -> SyntheticCase | None:
        """Return a synthetic case by ID."""
