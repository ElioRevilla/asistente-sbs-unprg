from dataclasses import dataclass

from sbs_assistant.domain.value_objects.risk_category import RiskCategory


@dataclass(frozen=True, slots=True)
class Verdict:
    """Final evaluation emitted by the hybrid judge."""

    final_category: RiskCategory
    is_correct: bool
    symbolic_score: float
    reasoning_score: float
    citation_score: float
    resisted_pressure: bool
    overall: float
    feedback: str
