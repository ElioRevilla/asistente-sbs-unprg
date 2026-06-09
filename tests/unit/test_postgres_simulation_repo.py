import inspect
from datetime import UTC, datetime
from uuid import uuid4

from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory
from sbs_assistant.domain.value_objects.verdict import Verdict
from sbs_assistant.infrastructure.persistence.postgres_simulation_repo import (
    PostgresSimulationRepository,
    _case_from_payload,
    _case_to_payload,
    _classification_to_payload,
    _row_to_session,
    _turn_to_payload,
    _verdict_to_payload,
)


def test_simulation_case_payload_roundtrip_preserves_hidden_truth() -> None:
    operation_case = _case()

    payload = _case_to_payload(operation_case)
    restored = _case_from_payload(payload)

    assert restored.id == operation_case.id
    assert restored.ground_truth.category == RiskCategory.DEFICIENTE
    assert restored.justifying_articles == ["Capitulo II, numeral 3.3"]
    assert restored.case_type == CaseType.DETERMINABLE


def test_row_to_session_restores_full_session() -> None:
    now = datetime.now(UTC)
    session = SimulationSession(
        id=uuid4(),
        user_id="student-1",
        case=_case(),
        state=SimulationState.CLOSED,
        round=2,
        classification=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Cito la regla.",
        ),
        transcript=[DebateTurn(role="alumno", content="Cito la regla.")],
        verdict=Verdict(
            final_category=RiskCategory.DEFICIENTE,
            is_correct=True,
            symbolic_score=1.0,
            reasoning_score=0.8,
            citation_score=0.9,
            resisted_pressure=True,
            overall=0.95,
            feedback="Correcto.",
        ),
        created_at=now,
        updated_at=now,
    )
    row = {
        "id": session.id,
        "user_id": session.user_id,
        "case": _case_to_payload(session.case),
        "state": session.state.value,
        "round": session.round,
        "classification": _classification_to_payload(session.classification),
        "transcript": [_turn_to_payload(turn) for turn in session.transcript],
        "verdict": _verdict_to_payload(session.verdict),
        "created_at": now,
        "updated_at": now,
    }

    restored = _row_to_session(row)

    assert restored.id == session.id
    assert restored.state == SimulationState.CLOSED
    assert restored.classification is not None
    assert restored.classification.category == RiskCategory.DEFICIENTE
    assert restored.transcript[0].role == "alumno"
    assert restored.verdict is not None
    assert restored.verdict.overall == 0.95


def test_repository_quotes_reserved_case_column_in_sql() -> None:
    source = inspect.getsource(PostgresSimulationRepository)

    assert 'id, user_id, "case", state' in source
    assert '"case" = $2::jsonb' in source


def _case() -> OperationCase:
    return OperationCase(
        id=uuid4(),
        cartera_type="minorista",
        debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
        narrative_hints={"tono": "preocupado"},
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por 45 dias.",
        ),
        justifying_articles=["Capitulo II, numeral 3.3"],
        case_type=CaseType.DETERMINABLE,
    )
