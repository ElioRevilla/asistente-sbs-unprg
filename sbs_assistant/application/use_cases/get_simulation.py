from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.use_cases.simulation_dtos import (
    SimulationView,
    to_simulation_view,
)
from sbs_assistant.domain.ports.simulation_repository_port import (
    SimulationRepositoryPort,
)


@dataclass(frozen=True, slots=True)
class GetSimulationRequest:
    """Input for loading a simulation session."""

    session_id: UUID


class GetSimulationUseCase:
    """Return a simulation session public view."""

    def __init__(self, repository: SimulationRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, request: GetSimulationRequest) -> SimulationView:
        session = await self._repository.get(request.session_id)
        if session is None:
            raise ValueError("No se encontro la simulacion indicada.")
        return to_simulation_view(session)
