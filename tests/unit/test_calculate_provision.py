from decimal import Decimal

import pytest

from sbs_assistant.application.use_cases.calculate_provision import (
    ProvisionCalculator,
)
from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


class FakeProvisionRuleRepository:
    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        self.rules = rules

    async def find_percentage(
        self,
        category: str,
        credit_type: str,
        guarantee_type: str,
    ) -> ProvisionRule | None:
        assert category == "Dudoso"
        assert credit_type == "consumo_no_revolvente"
        assert guarantee_type == "tabla_1_sin_garantia_o_no_cubierto"
        return ProvisionRule(
            category=Category.DUDOSO,
            credit_type=CreditType.CONSUMO,
            guarantee_type=guarantee_type,
            provision_percentage=Decimal("60.00"),
            source_article="Capitulo III, numeral 2.1 - Tabla 1",
        )


@pytest.mark.asyncio
async def test_calculator_classifies_minor_retail_case() -> None:
    calculator = ProvisionCalculator(repository=FakeProvisionRuleRepository())

    result = await calculator.try_calculate_from_question(
        "Tengo un deudor con un crédito de consumo no revolvente de "
        "S/ 10,000 con 75 días de atraso."
    )

    assert result is not None
    assert result.category == "Dudoso"
    assert result.credit_type == "consumo_no_revolvente"
    assert result.days_late == 75
    assert result.amount == Decimal("10000")
    assert result.provision_percentage == Decimal("60.00")
    assert result.provision_amount == Decimal("6000.00")
    assert result.classification_source == "Capítulo II, numeral 3.4"


@pytest.mark.asyncio
async def test_calculator_ignores_questions_without_amount_or_days() -> None:
    calculator = ProvisionCalculator(repository=FakeProvisionRuleRepository())

    result = await calculator.try_calculate_from_question(
        "Que significa credito de consumo no revolvente?"
    )

    assert result is None
