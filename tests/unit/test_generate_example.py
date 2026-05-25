from uuid import UUID, uuid4

import pytest

from sbs_assistant.application.use_cases.generate_example import (
    GenerateExampleRequest,
    GenerateExampleUseCase,
)
from sbs_assistant.application.use_cases.validate_example_answer import (
    ValidateExampleAnswerRequest,
    ValidateExampleAnswerUseCase,
)
from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.value_objects.credit_type import CreditType


class FakeSyntheticCaseRepository:
    def __init__(self) -> None:
        self.case_id = uuid4()
        self.saved_case: SyntheticCase | None = None

    async def save(self, case: SyntheticCase) -> SyntheticCase:
        self.saved_case = case
        return SyntheticCase(
            id=self.case_id,
            credit_type=case.credit_type,
            description=case.description,
            correct_category=case.correct_category,
            correct_provision=case.correct_provision,
            source_article=case.source_article,
            mode=case.mode,
        )

    async def get(self, case_id: UUID) -> SyntheticCase | None:
        if case_id != self.case_id or self.saved_case is None:
            return None
        return SyntheticCase(
            id=case_id,
            credit_type=self.saved_case.credit_type,
            description=self.saved_case.description,
            correct_category=self.saved_case.correct_category,
            correct_provision=self.saved_case.correct_provision,
            source_article=self.saved_case.source_article,
            mode=self.saved_case.mode,
        )


class FakeVariationService:
    def __init__(self) -> None:
        self.called = False

    async def vary(self, case: SyntheticCase, concept: str) -> SyntheticCase:
        self.called = True
        description = dict(case.description)
        description["nombre_deudor"] = "Negocios Vega"
        return SyntheticCase(
            id=case.id,
            credit_type=case.credit_type,
            description=description,
            correct_category=case.correct_category,
            correct_provision=case.correct_provision,
            source_article=case.source_article,
            mode=case.mode,
        )


@pytest.mark.asyncio
async def test_generate_example_uses_deterministic_template_for_deficiente() -> None:
    repository = FakeSyntheticCaseRepository()
    use_case = GenerateExampleUseCase(repository=repository)

    result = await use_case.execute(
        GenerateExampleRequest(concept="categoría Deficiente")
    )

    assert result.case_id == repository.case_id
    assert result.case_data["dias_atraso"] == 45
    assert result.source_article == "Capítulo II, numeral 3.3"
    assert "Deficiente" in result.options
    assert "Pérdida" in result.options


@pytest.mark.asyncio
async def test_generate_example_can_target_microempresa() -> None:
    repository = FakeSyntheticCaseRepository()
    use_case = GenerateExampleUseCase(repository=repository)

    result = await use_case.execute(
        GenerateExampleRequest(
            concept="microempresa en categorÃ­a Deficiente",
        )
    )

    assert repository.saved_case is not None
    assert repository.saved_case.credit_type == CreditType.MES
    assert result.case_data["tipo_credito"] == "microempresa"
    assert result.case_data["dias_atraso"] == 45
    assert result.case_data["monto"] == 10000.0
    assert result.source_article.endswith("numeral 3.3")


@pytest.mark.asyncio
async def test_generate_example_can_apply_optional_llm_variation() -> None:
    repository = FakeSyntheticCaseRepository()
    variation_service = FakeVariationService()
    use_case = GenerateExampleUseCase(
        repository=repository,
        variation_service=variation_service,
    )

    result = await use_case.execute(
        GenerateExampleRequest(
            concept="categorÃ­a Deficiente",
            use_llm_variation=True,
        )
    )

    assert variation_service.called is True
    assert result.case_data["nombre_deudor"] == "Negocios Vega"
    assert result.case_data["dias_atraso"] == 45
    assert result.source_article.endswith("numeral 3.3")


@pytest.mark.asyncio
async def test_validate_example_answer_returns_correct_feedback() -> None:
    repository = FakeSyntheticCaseRepository()
    generated = await GenerateExampleUseCase(repository=repository).execute(
        GenerateExampleRequest(concept="categoría Deficiente")
    )
    use_case = ValidateExampleAnswerUseCase(repository=repository)

    result = await use_case.execute(
        ValidateExampleAnswerRequest(
            case_id=generated.case_id,
            selected_category="Deficiente",
        )
    )

    assert result.correct is True
    assert result.correct_category == "Deficiente"
    assert "Correcto" in result.feedback


@pytest.mark.asyncio
async def test_validate_example_answer_returns_correction() -> None:
    repository = FakeSyntheticCaseRepository()
    generated = await GenerateExampleUseCase(repository=repository).execute(
        GenerateExampleRequest(concept="categoría Deficiente")
    )
    use_case = ValidateExampleAnswerUseCase(repository=repository)

    result = await use_case.execute(
        ValidateExampleAnswerRequest(
            case_id=generated.case_id,
            selected_category="CPP",
        )
    )

    assert result.correct is False
    assert result.correct_category == "Deficiente"
    assert "categoría correcta es Deficiente" in result.feedback
