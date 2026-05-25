import pytest

from sbs_assistant.application.use_cases.calculate_provision import ProvisionCalculator
from sbs_assistant.application.use_cases.explain_concept import (
    ExplainConceptRequest,
    ExplainConceptUseCase,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


class FakeRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.query: str | None = None
        self.top_k: int | None = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        self.query = query
        self.top_k = top_k
        return self.chunks


class FakeLLM:
    def __init__(
        self,
        answer: str = "La categoria Deficiente implica atraso relevante (Numeral 3.3).",
    ) -> None:
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None
        self.answer = answer

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.answer


class FakeProvisionRuleRepository:
    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        self.rules = rules

    async def find_percentage(
        self,
        category: str,
        credit_type: str,
        guarantee_type: str,
    ) -> ProvisionRule | None:
        return ProvisionRule(
            category=Category.DUDOSO,
            credit_type=CreditType.CONSUMO,
            guarantee_type=guarantee_type,
            provision_percentage=60,
            source_article="Capitulo III, numeral 2.1 - Tabla 1",
        )


@pytest.mark.asyncio
async def test_explain_concept_retrieves_context_and_generates_answer() -> None:
    retriever = FakeRetriever(
        chunks=[
            Chunk(
                id="sec_029_3_3",
                numeral="3.3",
                topics=["clasificacion", "cartera_minorista"],
                text="3.3 CATEGORIA DEFICIENTE. Atraso de 31 a 60 dias.",
            )
        ]
    )
    llm = FakeLLM()
    use_case = ExplainConceptUseCase(retriever=retriever, llm=llm)

    result = await use_case.execute(
        ExplainConceptRequest(question="Que es categoria deficiente?", top_k=3)
    )

    assert retriever.query == "Que es categoria deficiente?"
    assert retriever.top_k == 3
    assert "Deficiente" in result.answer
    assert result.citations[0].chunk_id == "sec_029_3_3"
    assert result.citations[0].label == "Numeral 3.3"
    assert llm.user_prompt is not None
    assert "CATEGORIA DEFICIENTE" in llm.user_prompt
    assert "Tipo de cartera: deudores minoristas" in llm.user_prompt
    assert "Temas: clasificacion, cartera_minorista" in llm.user_prompt


@pytest.mark.asyncio
async def test_explain_concept_answers_calculable_provision_by_code() -> None:
    retriever = FakeRetriever(
        chunks=[
            Chunk(
                id="sec_027_3_4",
                numeral="3.4",
                topics=["cartera_minorista"],
                text="3.4 CATEGORIA DUDOSO. Atraso de 61 a 120 dias.",
            )
        ]
    )
    llm = FakeLLM(answer="No deberia usarse para casos calculables.")
    use_case = ExplainConceptUseCase(
        retriever=retriever,
        llm=llm,
        provision_calculator=ProvisionCalculator(FakeProvisionRuleRepository()),
    )

    result = await use_case.execute(
        ExplainConceptRequest(
            question=(
                "Tengo un credito de consumo no revolvente de S/ 10,000 "
                "con 75 dias de atraso."
            )
        )
    )

    assert llm.user_prompt is None
    assert "categoría Dudoso" in result.answer
    assert "60%" in result.answer
    assert "S/ 6,000.00" in result.answer
    assert "Cálculo" in result.answer
    assert [citation.label for citation in result.citations] == [
        "Numeral 3.4",
        "Capítulo III, numeral 2.1 - Tabla 1",
    ]


@pytest.mark.asyncio
async def test_explain_concept_answers_credit_types_with_internal_plan() -> None:
    retriever = FakeRetriever(
        chunks=[
            Chunk(
                id="sec_004_4",
                numeral="4",
                text="4. TIPOS DE CRÉDITOS. La cartera se clasifica en ocho tipos.",
            ),
            Chunk(
                id="sec_005_4_1",
                numeral="4.1",
                text="4.1 CRÉDITOS CORPORATIVOS.",
            ),
            Chunk(
                id="sec_006_4_2",
                numeral="4.2",
                text="4.2 CRÉDITOS A GRANDES EMPRESAS.",
            ),
        ]
    )
    llm = FakeLLM(answer="No deberia usarse para listas cerradas.")
    use_case = ExplainConceptUseCase(retriever=retriever, llm=llm)

    result = await use_case.execute(
        ExplainConceptRequest(
            question="¿Cuántos tipos de crédito existen en el reglamento y cuáles son?",
            top_k=5,
        )
    )

    assert retriever.top_k == 10
    assert llm.user_prompt is None
    assert "ocho (8) tipos" in result.answer
    assert "Créditos a medianas empresas" in result.answer
    assert "Créditos hipotecarios para vivienda" in result.answer
    assert [citation.label for citation in result.citations] == ["Numeral 4"]


@pytest.mark.asyncio
async def test_explain_concept_answers_long_stay_risk_category_by_code() -> None:
    retriever = FakeRetriever(
        chunks=[
            Chunk(
                id="sec_040_2_1",
                numeral="2.1",
                text=(
                    "Cuando los deudores permanezcan clasificados en la "
                    "categoria Dudoso por mas de 36 meses o en la categoria "
                    "Perdida por mas de 24 meses, deben constituir provisiones "
                    "de acuerdo con las tasas senaladas en la Tabla 1."
                ),
            )
        ]
    )
    llm = FakeLLM(answer="No deberia usarse para reglas cerradas.")
    use_case = ExplainConceptUseCase(retriever=retriever, llm=llm)

    result = await use_case.execute(
        ExplainConceptRequest(
            question=(
                "¿Qué pasa con un deudor que permanece mucho tiempo en "
                "categoría Pérdida? ¿Hay alguna regla especial?"
            ),
            top_k=5,
        )
    )

    assert retriever.top_k == 10
    assert retriever.query is not None
    assert "Pérdida más de 24 meses" in retriever.query
    assert llm.user_prompt is None
    assert "Pérdida por más de 24 meses" in result.answer
    assert "100%" in result.answer
    assert [citation.label for citation in result.citations] == [
        "Numeral 2.1",
        "Capítulo III, numeral 2.1 - Tabla 1",
    ]


@pytest.mark.asyncio
async def test_explain_concept_returns_only_citations_used_in_answer() -> None:
    retriever = FakeRetriever(
        chunks=[
            Chunk(
                id="sec_015_5_2",
                numeral="5.2",
                text="5.2 CLASIFICACION CREDITICIA DEL DEUDOR. Criterios generales.",
            ),
            Chunk(
                id="sec_021_2_4",
                numeral="2.4",
                topics=["cartera_no_minorista"],
                text="2.4 CATEGORIA DUDOSO. Atrasos mayores a 120 dias.",
            ),
            Chunk(
                id="sec_027_3_4",
                numeral="3.4",
                topics=["cartera_minorista"],
                text="3.4 CATEGORIA DUDOSO. Atraso de 61 a 120 dias.",
            ),
        ]
    )
    llm = FakeLLM(
        answer=(
            "Depende del tipo de cartera: no minoristas (Numeral 2.4) "
            "y minoristas (Numeral 3.4)."
        )
    )
    use_case = ExplainConceptUseCase(retriever=retriever, llm=llm)

    result = await use_case.execute(
        ExplainConceptRequest(question="Cuando un deudor es Dudoso?")
    )

    assert [citation.label for citation in result.citations] == [
        "Numeral 2.4",
        "Numeral 3.4",
    ]


@pytest.mark.asyncio
async def test_explain_concept_returns_safe_fallback_without_context() -> None:
    use_case = ExplainConceptUseCase(retriever=FakeRetriever([]), llm=FakeLLM())

    result = await use_case.execute(ExplainConceptRequest(question="Algo fuera"))

    assert result.answer == (
        "No encontre informacion especifica en el reglamento para responder eso."
    )
    assert result.citations == []
