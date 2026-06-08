from decimal import Decimal
from uuid import uuid4

import pytest

from sbs_assistant.application.services.adversarial_judge import (
    AdversarialJudge,
    JudgeRubricResult,
)
from sbs_assistant.application.services.case_selector import (
    DeterministicSimulationCaseSelector,
)
from sbs_assistant.application.use_cases.calculate_provision import ProvisionCalculator
from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.domain.value_objects.risk_category import RiskCategory


class FakeProvisionRuleRepository:
    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        del rules

    async def find_percentage(
        self,
        category: str,
        credit_type: str,
        guarantee_type: str,
    ) -> ProvisionRule | None:
        del guarantee_type
        category_key = category.upper() if category != "Perdida" else "PERDIDA"
        return ProvisionRule(
            category=Category[category_key],
            credit_type=_credit_type_from_code(credit_type),
            guarantee_type="tabla_1_sin_garantia_o_no_cubierto",
            provision_percentage=Decimal("25.00"),
            source_article="Capitulo III, numeral 2.1 - Tabla 1",
        )


class FixedRubric:
    def __init__(
        self,
        *,
        reasoning_score: float,
        citation_score: float,
        resisted_pressure: bool = True,
    ) -> None:
        self.reasoning_score = reasoning_score
        self.citation_score = citation_score
        self.resisted_pressure = resisted_pressure

    async def evaluate_reasoning(
        self,
        session: SimulationSession,
        symbolic_score: float,
    ) -> JudgeRubricResult:
        del session, symbolic_score
        return JudgeRubricResult(
            reasoning_score=self.reasoning_score,
            citation_score=self.citation_score,
            resisted_pressure=self.resisted_pressure,
            feedback="Rubrica fija.",
        )


@pytest.mark.asyncio
async def test_case_selector_uses_template_truth_for_determinable_case() -> None:
    selector = DeterministicSimulationCaseSelector()

    operation_case = await selector.next_case(
        user_id="student-1",
        focus="microempresa en categoria Deficiente",
    )

    assert operation_case.case_type == CaseType.DETERMINABLE
    assert operation_case.cartera_type == "minorista"
    assert operation_case.debtor_profile["tipo_credito"] == "microempresa"
    assert operation_case.debtor_profile["dias_atraso"] == 45
    assert operation_case.ground_truth.category == RiskCategory.DEFICIENTE
    assert "45" in operation_case.ground_truth.justification
    assert operation_case.justifying_articles == ["Cap\u00edtulo II, numeral 3.3"]


@pytest.mark.asyncio
async def test_case_selector_can_validate_truth_with_provision_calculator() -> None:
    selector = DeterministicSimulationCaseSelector(
        provision_calculator=ProvisionCalculator(FakeProvisionRuleRepository())
    )

    operation_case = await selector.next_case(
        user_id="student-1",
        focus="microempresa en categoria Deficiente",
    )

    assert operation_case.ground_truth.category == RiskCategory.DEFICIENTE
    assert operation_case.justifying_articles == [
        "Cap\u00edtulo II, numeral 3.3",
        "Capitulo III, numeral 2.1 - Tabla 1",
    ]


@pytest.mark.asyncio
async def test_adversarial_judge_symbolic_score_dominates_determinable_case() -> None:
    judge = AdversarialJudge(
        rubric=FixedRubric(reasoning_score=1.0, citation_score=1.0)
    )
    session = _session(
        case_type=CaseType.DETERMINABLE,
        selected_category=RiskCategory.CPP,
    )

    verdict = await judge.evaluate(session)

    assert verdict.is_correct is False
    assert verdict.symbolic_score == 0.0
    assert verdict.reasoning_score == 1.0
    assert verdict.citation_score == 1.0
    assert verdict.overall == 0.3
    assert verdict.final_category == RiskCategory.DEFICIENTE


@pytest.mark.asyncio
async def test_adversarial_judge_weights_reasoning_more_in_judgment_case() -> None:
    judge = AdversarialJudge(
        rubric=FixedRubric(reasoning_score=1.0, citation_score=1.0)
    )
    session = _session(
        case_type=CaseType.JUDGMENT,
        selected_category=RiskCategory.CPP,
    )

    verdict = await judge.evaluate(session)

    assert verdict.is_correct is False
    assert verdict.overall == 0.65


@pytest.mark.asyncio
async def test_adversarial_judge_detects_bank_pressure_resistance() -> None:
    judge = AdversarialJudge()
    session = _session(
        case_type=CaseType.DETERMINABLE,
        selected_category=RiskCategory.DEFICIENTE,
    )

    verdict = await judge.evaluate(session)

    assert verdict.is_correct is True
    assert verdict.resisted_pressure is True
    assert verdict.overall > 0.7


def _session(
    *,
    case_type: CaseType,
    selected_category: RiskCategory,
) -> SimulationSession:
    operation_case = OperationCase(
        id=uuid4(),
        cartera_type="minorista",
        debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
        narrative_hints={},
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por 45 dias de atraso.",
        ),
        justifying_articles=["Capitulo II, numeral 3.3"],
        case_type=case_type,
    )
    return SimulationSession(
        id=uuid4(),
        user_id="student-1",
        case=operation_case,
        state=SimulationState.CLOSED,
        round=1,
        classification=Classification(
            category=selected_category,
            justification="Cito Capitulo II, numeral 3.3.",
        ),
        transcript=[
            DebateTurn(
                role="banco",
                content="El banco sugiere CPP.",
                metadata={"suggested_category": "CPP"},
            ),
            DebateTurn(
                role="alumno",
                content="Cito Capitulo II, numeral 3.3.",
            ),
        ],
    )


def _credit_type_from_code(credit_type: str) -> CreditType:
    return {
        "consumo_no_revolvente": CreditType.CONSUMO,
        "consumo_revolvente": CreditType.CONSUMO,
        "hipotecario": CreditType.HIPOTECARIO,
        "microempresa": CreditType.MES,
        "pequena_empresa": CreditType.PEQUENA_EMPRESA,
    }[credit_type]
