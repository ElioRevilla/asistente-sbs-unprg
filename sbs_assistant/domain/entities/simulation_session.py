from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.verdict import Verdict


class SimulationState(StrEnum):
    """Finite states for the adversarial simulation flow."""

    PRESENT = "present"
    CLASSIFY = "classify"
    CHALLENGE = "challenge"
    DEFEND = "defend"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class SimulationSession:
    """Persistent adversarial simulation session."""

    id: UUID
    user_id: str
    case: OperationCase
    state: SimulationState
    round: int = 0
    classification: Classification | None = None
    transcript: list[DebateTurn] = field(default_factory=list)
    verdict: Verdict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
