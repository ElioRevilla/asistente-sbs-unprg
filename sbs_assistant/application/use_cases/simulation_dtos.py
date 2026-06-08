from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory
from sbs_assistant.domain.value_objects.verdict import Verdict


@dataclass(frozen=True, slots=True)
class ClassificationView:
    """Public view of a classification."""

    category: str
    justification: str


@dataclass(frozen=True, slots=True)
class VerdictView:
    """Public view of a final verdict."""

    final_category: str
    is_correct: bool
    symbolic_score: float
    reasoning_score: float
    citation_score: float
    resisted_pressure: bool
    overall: float
    feedback: str


@dataclass(frozen=True, slots=True)
class DebateTurnView:
    """Public view of one transcript turn."""

    role: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OperationCaseView:
    """Public case view, optionally exposing hidden truth after closure."""

    id: UUID
    cartera_type: str
    debtor_profile: dict[str, object]
    narrative_hints: dict[str, object]
    case_type: str
    ground_truth: ClassificationView | None = None
    justifying_articles: list[str] | None = None


@dataclass(frozen=True, slots=True)
class SimulationView:
    """Public view of a simulation session."""

    id: UUID
    user_id: str
    state: str
    round: int
    case: OperationCaseView
    classification: ClassificationView | None
    transcript: list[DebateTurnView]
    verdict: VerdictView | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


def parse_risk_category(value: str) -> RiskCategory:
    """Parse a risk category from user-facing text."""
    normalized = value.strip().lower()
    normalized = normalized.replace("é", "e")
    for category in RiskCategory:
        category_value = category.value.lower().replace("é", "e")
        if normalized == category_value:
            return category
    raise ValueError(f"Categoria de riesgo invalida: {value}")


def to_simulation_view(session: SimulationSession) -> SimulationView:
    """Convert a domain session to a public view without leaking hidden truth."""
    expose_truth = session.state == SimulationState.CLOSED
    return SimulationView(
        id=session.id,
        user_id=session.user_id,
        state=session.state.value,
        round=session.round,
        case=_case_view(session.case, expose_truth=expose_truth),
        classification=_classification_view(session.classification),
        transcript=[_turn_view(turn) for turn in session.transcript],
        verdict=_verdict_view(session.verdict),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _case_view(
    operation_case: OperationCase,
    *,
    expose_truth: bool,
) -> OperationCaseView:
    return OperationCaseView(
        id=operation_case.id,
        cartera_type=operation_case.cartera_type,
        debtor_profile=operation_case.debtor_profile,
        narrative_hints=operation_case.narrative_hints,
        case_type=operation_case.case_type.value,
        ground_truth=(
            _classification_view(operation_case.ground_truth) if expose_truth else None
        ),
        justifying_articles=(
            list(operation_case.justifying_articles) if expose_truth else None
        ),
    )


def _classification_view(
    classification: Classification | None,
) -> ClassificationView | None:
    if classification is None:
        return None
    return ClassificationView(
        category=classification.category.value,
        justification=classification.justification,
    )


def _turn_view(turn: DebateTurn) -> DebateTurnView:
    return DebateTurnView(
        role=turn.role,
        content=turn.content,
        metadata=turn.metadata,
        created_at=turn.created_at,
    )


def _verdict_view(verdict: Verdict | None) -> VerdictView | None:
    if verdict is None:
        return None
    return VerdictView(
        final_category=verdict.final_category.value,
        is_correct=verdict.is_correct,
        symbolic_score=verdict.symbolic_score,
        reasoning_score=verdict.reasoning_score,
        citation_score=verdict.citation_score,
        resisted_pressure=verdict.resisted_pressure,
        overall=verdict.overall,
        feedback=verdict.feedback,
    )
