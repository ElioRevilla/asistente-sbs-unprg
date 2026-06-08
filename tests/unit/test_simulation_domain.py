from pathlib import Path
from uuid import uuid4

from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory


def test_risk_category_order_supports_pressure_comparison() -> None:
    assert RiskCategory.CPP.is_higher_than(RiskCategory.NORMAL)
    assert RiskCategory.DEFICIENTE.is_lower_than(RiskCategory.DUDOSO)
    assert RiskCategory.PERDIDA.order == 4


def test_simulation_session_keeps_ground_truth_inside_case() -> None:
    operation_case = OperationCase(
        id=uuid4(),
        cartera_type="minorista",
        debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
        narrative_hints={"tono": "cliente preocupado"},
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Atraso de 31 a 60 dias calendario.",
        ),
        justifying_articles=["Capitulo II, numeral 3.3"],
        case_type=CaseType.DETERMINABLE,
    )

    session = SimulationSession(
        id=uuid4(),
        user_id="student-1",
        case=operation_case,
        state=SimulationState.CLASSIFY,
    )

    assert session.classification is None
    assert session.verdict is None
    assert session.transcript == []
    assert session.case.ground_truth.category == RiskCategory.DEFICIENTE


def test_domain_layer_has_no_infrastructure_imports() -> None:
    domain_root = Path("sbs_assistant/domain")
    forbidden_terms = (
        "fastapi",
        "asyncpg",
        "psycopg",
        "google.cloud",
        "firebase",
        "sbs_assistant.infrastructure",
        "sbs_assistant.api",
    )

    for path in domain_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in source, f"{path} imports or references {term}"
