from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.services.debate_orchestrator import (
    DebateOrchestrator,
)
from sbs_assistant.application.use_cases.simulation_dtos import (
    SimulationView,
    to_simulation_view,
)
from sbs_assistant.domain.ports.simulation_repository_port import (
    SimulationRepositoryPort,
)


@dataclass(frozen=True, slots=True)
class AdvanceDebateRequest:
    """Student defense for an adversarial simulation turn."""

    session_id: UUID
    defense: str


class AdvanceDebateUseCase:
    """Advance the adversarial debate after a student defense."""

    def __init__(
        self,
        *,
        repository: SimulationRepositoryPort,
        orchestrator: DebateOrchestrator,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator

    async def execute(self, request: AdvanceDebateRequest) -> SimulationView:
        session = await self._repository.get(request.session_id)
        if session is None:
            raise ValueError("No se encontro la simulacion indicada.")
        updated = await self._orchestrator.advance_defense(
            session,
            defense=request.defense,
        )
        saved = await self._repository.update(updated)
        return to_simulation_view(saved)
