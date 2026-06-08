from typing import Protocol
from uuid import UUID

from sbs_assistant.domain.entities.simulation_session import SimulationSession


class SimulationRepositoryPort(Protocol):
    """Persistence port for adversarial simulation sessions."""

    async def create(self, session: SimulationSession) -> SimulationSession:
        """Persist a new simulation session."""

    async def get(self, session_id: UUID) -> SimulationSession | None:
        """Return a simulation session by ID."""

    async def update(self, session: SimulationSession) -> SimulationSession:
        """Persist changes to an existing simulation session."""

    async def list_by_user(self, user_id: str) -> list[SimulationSession]:
        """Return simulation sessions for a user."""
