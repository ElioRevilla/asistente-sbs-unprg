from dataclasses import dataclass, field
from uuid import UUID

from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification


@dataclass(frozen=True, slots=True)
class OperationCase:
    """Credit operation case used in adversarial simulations."""

    id: UUID
    cartera_type: str
    debtor_profile: dict[str, object]
    narrative_hints: dict[str, object]
    ground_truth: Classification
    justifying_articles: list[str] = field(default_factory=list)
    case_type: CaseType = CaseType.DETERMINABLE
