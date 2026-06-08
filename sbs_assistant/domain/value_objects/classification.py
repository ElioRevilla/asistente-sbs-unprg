from dataclasses import dataclass

from sbs_assistant.domain.value_objects.risk_category import RiskCategory


@dataclass(frozen=True, slots=True)
class Classification:
    """Student or ground-truth classification for an operation case."""

    category: RiskCategory
    justification: str
