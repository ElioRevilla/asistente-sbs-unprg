from dataclasses import dataclass

from sbs_assistant.application.prompts.explain import EXPLAIN_SYSTEM_PROMPT
from sbs_assistant.application.services.retrieval_planner import (
    PlannedAnswer,
    RetrievalPlanner,
)
from sbs_assistant.application.use_cases.calculate_provision import (
    ProvisionCalculation,
    ProvisionCalculator,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.ports.llm_port import LLMPort
from sbs_assistant.domain.ports.retriever_port import RetrieverPort


@dataclass(frozen=True, slots=True)
class Citation:
    """Source citation exposed to the API layer."""

    chunk_id: str
    label: str
    text_preview: str


@dataclass(frozen=True, slots=True)
class ExplainConceptRequest:
    """Input for the Explícame pedagogical mode."""

    question: str
    top_k: int = 5


@dataclass(frozen=True, slots=True)
class ExplainConceptResult:
    """Pedagogical explanation grounded in retrieved regulation chunks."""

    answer: str
    citations: list[Citation]


class ExplainConceptUseCase:
    """Explain a regulatory concept using retrieved SBS regulation context."""

    def __init__(
        self,
        retriever: RetrieverPort,
        llm: LLMPort,
        provision_calculator: ProvisionCalculator | None = None,
        retrieval_planner: RetrievalPlanner | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._provision_calculator = provision_calculator
        self._retrieval_planner = retrieval_planner or RetrievalPlanner()

    async def execute(self, request: ExplainConceptRequest) -> ExplainConceptResult:
        retrieval_plan = self._retrieval_planner.plan(
            question=request.question,
            requested_top_k=request.top_k,
        )
        retrieval_query = retrieval_plan.query or request.question
        chunks = await self._retriever.retrieve(
            retrieval_query,
            top_k=retrieval_plan.top_k,
        )
        if not chunks:
            return ExplainConceptResult(
                answer=(
                    "No encontre informacion especifica en el reglamento para "
                    "responder eso."
                ),
                citations=[],
            )

        if retrieval_plan.answer_strategy == PlannedAnswer.CREDIT_TYPES:
            return self._build_credit_types_result(chunks)
        if retrieval_plan.answer_strategy == PlannedAnswer.LONG_STAY_RISK_CATEGORY:
            return self._build_long_stay_risk_category_result(chunks)

        provision_calculation = None
        if self._provision_calculator is not None:
            provision_calculation = (
                await self._provision_calculator.try_calculate_from_question(
                    request.question
                )
            )
        if provision_calculation is not None:
            return ExplainConceptResult(
                answer=self._build_provision_answer(provision_calculation),
                citations=[
                    *self._classification_citations(
                        chunks=chunks,
                        calculation=provision_calculation,
                    ),
                    self._provision_citation(provision_calculation),
                ],
            )

        user_prompt = self._build_user_prompt(
            question=request.question,
            chunks=chunks,
            deterministic_context=(
                self._format_provision_calculation(provision_calculation)
                if provision_calculation
                else None
            ),
        )
        answer = await self._llm.generate(
            system_prompt=EXPLAIN_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        clean_answer = answer.strip()
        return ExplainConceptResult(
            answer=clean_answer,
            citations=self._citations_from_answer(chunks=chunks, answer=clean_answer),
        )

    def _build_user_prompt(
        self,
        question: str,
        chunks: list[Chunk],
        deterministic_context: str | None = None,
    ) -> str:
        context = "\n\n".join(
            "\n".join(
                [
                    f"Fuente {index}: {self._source_label(chunk)}",
                    f"Tipo de cartera: {self._portfolio_label(chunk)}",
                    f"Temas: {', '.join(chunk.topics) or 'sin metadata'}",
                    chunk.text,
                ]
            )
            for index, chunk in enumerate(chunks, start=1)
        )
        deterministic_block = (
            f"\n\nCálculo determinístico disponible:\n{deterministic_context}"
            if deterministic_context
            else ""
        )
        return f"""
Pregunta del estudiante:
{question}

Contexto recuperado del reglamento:
{context}
{deterministic_block}

Explica la respuesta usando solo ese contexto. Si existe un cálculo
determinístico disponible, debes usar sus valores exactos para la categoría,
porcentaje y monto de provisión. Cita las fuentes por artículo, numeral o anexo.
""".strip()

    def _citation_from_chunk(self, chunk: Chunk) -> Citation:
        return Citation(
            chunk_id=chunk.id,
            label=self._source_label(chunk),
            text_preview=" ".join(chunk.text.split())[:240],
        )

    def _build_credit_types_result(self, chunks: list[Chunk]) -> ExplainConceptResult:
        answer = (
            "El reglamento clasifica la cartera de créditos en ocho (8) tipos "
            "(Numeral 4):\n\n"
            "1. Créditos corporativos.\n"
            "2. Créditos a grandes empresas.\n"
            "3. Créditos a medianas empresas.\n"
            "4. Créditos a pequeñas empresas.\n"
            "5. Créditos a microempresas.\n"
            "6. Créditos de consumo revolvente.\n"
            "7. Créditos de consumo no revolvente.\n"
            "8. Créditos hipotecarios para vivienda."
        )
        citation_chunks = [chunk for chunk in chunks if chunk.numeral == "4"]
        if not citation_chunks:
            citation_chunks = chunks[:1]
        return ExplainConceptResult(
            answer=answer,
            citations=[self._citation_from_chunk(chunk) for chunk in citation_chunks],
        )

    def _build_long_stay_risk_category_result(
        self,
        chunks: list[Chunk],
    ) -> ExplainConceptResult:
        answer = (
            "Sí. El reglamento establece una regla especial cuando un deudor "
            "permanece mucho tiempo en categorías de mayor riesgo.\n\n"
            "Si el deudor permanece clasificado como Dudoso por más de 36 meses "
            "o como Pérdida por más de 24 meses, debe constituir provisiones "
            "según las tasas de la Tabla 1, independientemente del tipo de "
            "crédito y de la garantía que tenga.\n\n"
            "Para la categoría Pérdida, la Tabla 1 exige una provisión de "
            "100%.\n\n"
            "Esta regla no aplica cuando la clasificación proviene del "
            "procedimiento de alineamiento, ni en ciertos créditos hipotecarios "
            "para vivienda en situación contable vigente vinculados al literal "
            "c) del numeral 5.2 del Capítulo I."
        )
        citations = self._long_stay_citations(chunks)
        citations.append(
            Citation(
                chunk_id="provision_rules:Perdida:tabla_1_sin_garantia_o_no_cubierto",
                label="Capítulo III, numeral 2.1 - Tabla 1",
                text_preview=(
                    "Categoría Pérdida; Tabla 1: sin garantía o parte no "
                    "cubierta por garantía; porcentaje de provisión 100.00%."
                ),
            )
        )
        return ExplainConceptResult(answer=answer, citations=citations)

    def _citations_from_answer(
        self, chunks: list[Chunk], answer: str
    ) -> list[Citation]:
        cited_chunks = [
            chunk
            for chunk in chunks
            if self._source_label(chunk).lower() in answer.lower()
        ]
        if not cited_chunks:
            cited_chunks = chunks
        return [self._citation_from_chunk(chunk) for chunk in cited_chunks]

    def _long_stay_citations(self, chunks: list[Chunk]) -> list[Citation]:
        matching_chunks = [
            chunk
            for chunk in chunks
            if "permanezcan clasificados" in chunk.text.lower()
            or "pérdida por más de 24 meses" in chunk.text.lower()
            or "perdida por mas de 24 meses" in chunk.text.lower()
            or "dudoso por más de 36 meses" in chunk.text.lower()
            or "dudoso por mas de 36 meses" in chunk.text.lower()
        ]
        if matching_chunks:
            return [
                self._long_stay_citation_from_chunk(chunk)
                for chunk in matching_chunks[:1]
            ]
        return [
            Citation(
                chunk_id="regla_permanencia:categorias_riesgosas",
                label="Capítulo III, numeral 2.1",
                text_preview=(
                    "Dudoso por más de 36 meses o Pérdida por más de 24 "
                    "meses: aplicar tasas de la Tabla 1."
                ),
            )
        ]

    def _long_stay_citation_from_chunk(self, chunk: Chunk) -> Citation:
        compact_text = " ".join(chunk.text.split())
        lowered = compact_text.lower()
        start = lowered.find("permanezcan clasificados")
        if start < 0:
            start = lowered.find("pérdida por más de 24 meses")
        if start < 0:
            start = lowered.find("perdida por mas de 24 meses")
        if start < 0:
            start = 0
        preview = compact_text[max(0, start - 80) : start + 320]
        return Citation(
            chunk_id=chunk.id,
            label=self._source_label(chunk),
            text_preview=preview,
        )

    def _source_label(self, chunk: Chunk) -> str:
        if chunk.article is not None:
            return f"Articulo {chunk.article}"
        if chunk.numeral:
            return f"Numeral {chunk.numeral}"
        if chunk.chapter:
            return chunk.chapter
        return chunk.id

    def _portfolio_label(self, chunk: Chunk) -> str:
        if "cartera_no_minorista" in chunk.topics:
            return (
                "deudores no minoristas: corporativos, grandes empresas "
                "y medianas empresas"
            )
        if "cartera_minorista" in chunk.topics:
            return (
                "deudores minoristas: pequenas empresas, microempresas, "
                "consumo revolvente y consumo no revolvente"
            )
        if "cartera_hipotecaria_vivienda" in chunk.topics:
            return "creditos hipotecarios para vivienda"
        return "no especificado en metadata"

    def _format_provision_calculation(
        self,
        calculation: ProvisionCalculation,
    ) -> str:
        return (
            f"Tipo de crédito: {calculation.credit_type}\n"
            f"Días de atraso: {calculation.days_late}\n"
            f"Categoría calculada por código: {calculation.category}\n"
            f"Monto del crédito: S/ {calculation.amount:,.2f}\n"
            f"Tipo de garantía asumida: {calculation.guarantee_type}\n"
            f"Porcentaje de provisión calculado por código: "
            f"{calculation.provision_percentage}%\n"
            f"Monto de provisión calculado por código: "
            f"S/ {calculation.provision_amount:,.2f}\n"
            f"Fuente de clasificación: {calculation.classification_source}\n"
            f"Fuente de provisión: {calculation.provision_source}\n"
            "Si la pregunta no menciona garantía, explicar que se asumió la "
            "Tabla 1: sin garantía o parte no cubierta por garantía."
        )

    def _build_provision_answer(self, calculation: ProvisionCalculation) -> str:
        guarantee_note = (
            "Como la pregunta no menciona garantía, se asume la Tabla 1: "
            "sin garantía o parte no cubierta por garantía."
            if calculation.guarantee_type == "tabla_1_sin_garantia_o_no_cubierto"
            else f"Se usa la regla de garantía: {calculation.guarantee_type}."
        )
        return (
            f"El deudor va en categoría {calculation.category}. Para este tipo "
            f"de crédito, {calculation.days_late} días de atraso caen en esa "
            f"categoría ({calculation.classification_source}).\n\n"
            f"{guarantee_note} La tasa de provisión aplicable es "
            f"{calculation.provision_percentage}% "
            f"({self._display_source(calculation.provision_source)}).\n\n"
            f"Cálculo: S/ {calculation.amount:,.2f} × "
            f"{calculation.provision_percentage}% = "
            f"S/ {calculation.provision_amount:,.2f}."
        )

    def _classification_citations(
        self,
        chunks: list[Chunk],
        calculation: ProvisionCalculation,
    ) -> list[Citation]:
        source = calculation.classification_source.lower()
        citations = [
            self._citation_from_chunk(chunk)
            for chunk in chunks
            if chunk.numeral and f"numeral {chunk.numeral}" in source
        ]
        if not citations:
            citations.append(
                Citation(
                    chunk_id=f"classification:{calculation.category}",
                    label=calculation.classification_source,
                    text_preview=(
                        f"Clasificación calculada por días de atraso: "
                        f"{calculation.category}."
                    ),
                )
            )
        return citations

    def _provision_citation(self, calculation: ProvisionCalculation) -> Citation:
        return Citation(
            chunk_id=(
                f"provision_rules:{calculation.category}:"
                f"{calculation.guarantee_type}"
            ),
            label=self._display_source(calculation.provision_source),
            text_preview=(
                f"Categoría {calculation.category}; "
                f"tipo de garantía {calculation.guarantee_type}; "
                f"porcentaje de provisión {calculation.provision_percentage}%."
            ),
        )

    def _display_source(self, source: str) -> str:
        return source.replace("Capitulo", "Capítulo")
