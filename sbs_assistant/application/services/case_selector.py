from dataclasses import dataclass
from uuid import uuid4

from sbs_assistant.application.services.example_case_templates import (
    TemplateExampleCaseGenerator,
)
from sbs_assistant.application.use_cases.calculate_provision import (
    ProvisionCalculator,
)
from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.ports.case_selector_port import CaseSelectorPort
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory

DEFAULT_SIMULATION_FOCUS = "microempresa en categoria Deficiente"


@dataclass(frozen=True, slots=True)
class SelectedCaseTruth:
    """Ground truth selected for an operation case."""

    category: RiskCategory
    justification: str
    articles: list[str]


class DeterministicSimulationCaseSelector(CaseSelectorPort):
    """Select simulation cases deterministically from auditable templates."""

    def __init__(
        self,
        *,
        generator: TemplateExampleCaseGenerator | None = None,
        provision_calculator: ProvisionCalculator | None = None,
    ) -> None:
        self._generator = generator or TemplateExampleCaseGenerator()
        self._provision_calculator = provision_calculator

    async def next_case(
        self,
        user_id: str,
        focus: str | None = None,
    ) -> OperationCase:
        """Return the next operation case with hidden ground truth."""
        del user_id
        concept = focus or DEFAULT_SIMULATION_FOCUS
        synthetic_case = self._generator.generate(concept)
        truth = await self._truth_for_case(synthetic_case)
        return OperationCase(
            id=uuid4(),
            cartera_type=self._cartera_type(synthetic_case),
            debtor_profile=self._debtor_profile(synthetic_case),
            narrative_hints=self._narrative_hints(synthetic_case),
            ground_truth=Classification(
                category=truth.category,
                justification=truth.justification,
            ),
            justifying_articles=truth.articles,
            case_type=CaseType.DETERMINABLE,
        )

    async def _truth_for_case(
        self,
        synthetic_case: SyntheticCase,
    ) -> SelectedCaseTruth:
        calculated = None
        if self._provision_calculator is not None:
            calculated = await self._provision_calculator.try_calculate_from_question(
                self._calculation_question(synthetic_case),
            )

        if calculated is not None:
            category = _risk_category_from_text(calculated.category)
            return SelectedCaseTruth(
                category=category,
                justification=(
                    f"Categoria {category.value} por "
                    f"{calculated.days_late} dias de atraso."
                ),
                articles=[
                    calculated.classification_source,
                    calculated.provision_source,
                ],
            )

        if synthetic_case.correct_category is None:
            raise ValueError("Simulation case template must include ground truth.")
        category = _risk_category_from_category(synthetic_case.correct_category)
        return SelectedCaseTruth(
            category=category,
            justification=self._template_justification(synthetic_case, category),
            articles=[synthetic_case.source_article or "Reglamento SBS"],
        )

    def _debtor_profile(self, synthetic_case: SyntheticCase) -> dict[str, object]:
        description = dict(synthetic_case.description)
        description["credit_type_code"] = synthetic_case.credit_type.value
        return description

    def _narrative_hints(self, synthetic_case: SyntheticCase) -> dict[str, object]:
        debtor_name = synthetic_case.description.get("nombre_deudor", "deudor")
        return {
            "client_bias": (
                "presentar el caso con simpatia y deseo de conservar credito"
            ),
            "debtor_name": debtor_name,
            "visible_pressure": "el banco preferiria una categoria de menor provision",
        }

    def _cartera_type(self, synthetic_case: SyntheticCase) -> str:
        credit_label = str(synthetic_case.description.get("tipo_credito", ""))
        if "hipotecario" in credit_label:
            return "hipotecaria_vivienda"
        if credit_label in {
            "microempresa",
            "pequena empresa",
            "consumo revolvente",
            "consumo no revolvente",
        }:
            return "minorista"
        return "no_minorista"

    def _calculation_question(self, synthetic_case: SyntheticCase) -> str:
        description = synthetic_case.description
        credit_type = description.get("tipo_credito", "")
        amount = description.get("monto", "")
        days_late = description.get("dias_atraso", "")
        return (
            f"Tengo un deudor con credito de {credit_type} de S/ {amount} "
            f"con {days_late} dias de atraso."
        )

    def _template_justification(
        self,
        synthetic_case: SyntheticCase,
        category: RiskCategory,
    ) -> str:
        days_late = synthetic_case.description.get("dias_atraso")
        credit_type = synthetic_case.description.get("tipo_credito")
        return (
            f"Categoria {category.value} para credito {credit_type} "
            f"por {days_late} dias de atraso."
        )


def _risk_category_from_category(category: Category) -> RiskCategory:
    return RiskCategory[category.name]


def _risk_category_from_text(value: str) -> RiskCategory:
    normalized = value.strip().lower().replace("é", "e")
    for category in RiskCategory:
        if normalized == category.value.lower().replace("é", "e"):
            return category
    raise ValueError(f"Unknown risk category: {value}")
