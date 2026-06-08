from dataclasses import dataclass
from uuid import uuid4

from sbs_assistant.application.services.debate_orchestrator import (
    DebateOrchestrator,
)
from sbs_assistant.application.use_cases.simulation_dtos import (
    SimulationView,
    to_simulation_view,
)
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.ports.case_selector_port import CaseSelectorPort
from sbs_assistant.domain.ports.simulation_repository_port import (
    SimulationRepositoryPort,
)


@dataclass(frozen=True, slots=True)
class StartSimulationRequest:
    """Input for starting an adversarial simulation."""

    user_id: str
    focus: str | None = None


class StartSimulationUseCase:
    """Start an adversarial simulation and present the case."""

    def __init__(
        self,
        *,
        case_selector: CaseSelectorPort,
        repository: SimulationRepositoryPort,
        orchestrator: DebateOrchestrator,
    ) -> None:
        self._case_selector = case_selector
        self._repository = repository
        self._orchestrator = orchestrator

    async def execute(self, request: StartSimulationRequest) -> SimulationView:
        operation_case = await self._case_selector.next_case(
            user_id=request.user_id,
            focus=request.focus,
        )
        session = SimulationSession(
            id=uuid4(),
            user_id=request.user_id,
            case=operation_case,
            state=SimulationState.PRESENT,
        )
        created = await self._repository.create(session)
        presented = await self._orchestrator.present_case(created)
        saved = await self._repository.update(presented)
        return to_simulation_view(saved)
