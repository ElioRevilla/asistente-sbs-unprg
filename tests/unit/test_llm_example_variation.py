from decimal import Decimal

import pytest

from sbs_assistant.application.services.llm_example_variation import (
    LLMExampleCaseVariationService,
)
from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.domain.value_objects.pedagogical_mode import PedagogicalMode


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response


def _base_case() -> SyntheticCase:
    return SyntheticCase(
        id=None,
        credit_type=CreditType.CONSUMO,
        description={
            "nombre_deudor": "Distribuidora Norte",
            "tipo_credito": "consumo no revolvente",
            "monto": 10000.0,
            "dias_atraso": 45,
            "situacion": "sus ingresos bajaron y viene acumulando retrasos",
            "pregunta": "En que categoria crediticia clasificarias a este deudor?",
        },
        correct_category=Category.DEFICIENTE,
        correct_provision=Decimal("0.00"),
        source_article="Capitulo II, numeral 3.3",
        mode=PedagogicalMode.EJEMPLIFICA,
    )


@pytest.mark.asyncio
async def test_llm_variation_only_updates_safe_narrative_fields() -> None:
    llm = FakeLLM("""
        {
          "nombre_deudor": "Bodega Las Palmas",
          "rubro": "comercio minorista",
          "situacion": "tuvo una caida temporal de ventas",
          "tipo_credito": "hipotecario",
          "monto": 999999,
          "dias_atraso": 2,
          "categoria_correcta": "Normal"
        }
        """)
    service = LLMExampleCaseVariationService(llm=llm)

    varied = await service.vary(case=_base_case(), concept="categoria Deficiente")

    assert varied.description["nombre_deudor"] == "Bodega Las Palmas"
    assert varied.description["rubro"] == "comercio minorista"
    assert varied.description["situacion"] == "tuvo una caida temporal de ventas"
    assert varied.description["tipo_credito"] == "consumo no revolvente"
    assert varied.description["monto"] == 10000.0
    assert varied.description["dias_atraso"] == 45
    assert varied.correct_category == Category.DEFICIENTE
    assert varied.source_article == "Capitulo II, numeral 3.3"


@pytest.mark.asyncio
async def test_llm_variation_returns_original_case_when_response_is_not_json() -> None:
    base_case = _base_case()
    service = LLMExampleCaseVariationService(llm=FakeLLM("respuesta no json"))

    varied = await service.vary(case=base_case, concept="categoria Deficiente")

    assert varied == base_case
