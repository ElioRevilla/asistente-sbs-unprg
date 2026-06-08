from typing import Protocol

from sbs_assistant.domain.entities.agent_turn import (
    BancoTurnDTO,
    ClienteTurnDTO,
    SupervisorTurnDTO,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.value_objects.classification import Classification


class DebateAgentPort(Protocol):
    """Port for bounded LLM calls by the diegetic debate agents."""

    async def present(self, case: OperationCase) -> ClienteTurnDTO:
        """Return the client narrative without exposing ground truth."""

    async def challenge(
        self,
        case: OperationCase,
        ground_truth: Classification,
        grounding_chunks: list[Chunk],
        last_defense: str | None,
        prior_objections: list[str],
    ) -> SupervisorTurnDTO:
        """Return a grounded supervisor challenge."""

    async def pressure(
        self,
        case: OperationCase,
        current_classification: Classification,
    ) -> BancoTurnDTO:
        """Return bank pressure without exposing ground truth."""
