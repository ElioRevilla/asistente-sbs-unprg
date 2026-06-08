from typing import Protocol

from sbs_assistant.domain.entities.simulation_session import SimulationSession
from sbs_assistant.domain.value_objects.verdict import Verdict


class JudgePort(Protocol):
    """Port for the hybrid adversarial simulation judge."""

    async def evaluate(self, session: SimulationSession) -> Verdict:
        """Evaluate a closed debate candidate and return a verdict."""
