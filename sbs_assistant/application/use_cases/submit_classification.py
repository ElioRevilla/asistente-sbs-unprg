from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.services.debate_orchestrator import (
    DebateOrchestrator,
)
from sbs_assistant.application.use_cases.simulation_dtos import (
    SimulationView,
    parse_risk_category,
    to_simulation_view,
)
from sbs_assistant.domain.ports.simulation_repository_port import (
    SimulationRepositoryPort,
)
from sbs_assistant.domain.value_objects.classification import Classification


@dataclass(frozen=True, slots=True)
class SubmitClassificationRequest:
    """Student classification for an adversarial simulation."""

    session_id: UUID
    category: str
    justification: str


class SubmitClassificationUseCase:
    """Register the initial student classification and start the challenge."""

    def __init__(
        self,
        *,
        repository: SimulationRepositoryPort,
        orchestrator: DebateOrchestrator,
    ) -> None:
        self._repository = repository
        self._orchestrator = orchestrator

    async def execute(self, request: SubmitClassificationRequest) -> SimulationView:
        session = await self._repository.get(request.session_id)
        if session is None:
            raise ValueError("No se encontro la simulacion indicada.")
        classification = Classification(
            category=parse_risk_category(request.category),
            justification=request.justification,
        )
        updated = await self._orchestrator.submit_classification(
            session,
            classification,
        )
        saved = await self._repository.update(updated)
        return to_simulation_view(saved)
