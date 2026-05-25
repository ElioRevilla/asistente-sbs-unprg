from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.schemas.request_schemas import ExplainRequest
from sbs_assistant.api.schemas.response_schemas import (
    CitationResponse,
    ExplainDataResponse,
    ExplainResponse,
)
from sbs_assistant.application.use_cases.calculate_provision import ProvisionCalculator
from sbs_assistant.application.use_cases.explain_concept import (
    ExplainConceptRequest,
    ExplainConceptResult,
    ExplainConceptUseCase,
)
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.embeddings.vertex_embeddings import VertexEmbeddings
from sbs_assistant.infrastructure.llm.vertex_gemini_client import VertexGeminiClient
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)
from sbs_assistant.infrastructure.persistence.postgres_provision_rule_repo import (
    PostgresProvisionRuleRepository,
)
from sbs_assistant.infrastructure.retrieval.postgres_hybrid_retriever import (
    PostgresHybridRetriever,
)

router = APIRouter(prefix="/modes", tags=["modes"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUserDependency = Annotated[FirebaseUser | None, Depends(get_current_user)]


async def get_explain_use_case(
    settings: SettingsDependency,
) -> AsyncIterator[ExplainConceptUseCase]:
    """Build the Explícame use case for API requests."""
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required for Explícame mode")

    pool = await create_pool(settings)
    try:
        embeddings = VertexEmbeddings(
            project_id=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            model_name=settings.embeddings_model,
        )
        retriever = PostgresHybridRetriever(pool=pool, embeddings=embeddings)
        llm = VertexGeminiClient(
            project_id=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_flash_model,
        )
        provision_calculator = ProvisionCalculator(
            repository=PostgresProvisionRuleRepository(pool=pool)
        )
        yield ExplainConceptUseCase(
            retriever=retriever,
            llm=llm,
            provision_calculator=provision_calculator,
        )
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


@router.post("/explain", response_model=ExplainResponse)
async def explain(
    request: ExplainRequest,
    use_case: Annotated[ExplainConceptUseCase, Depends(get_explain_use_case)],
    current_user: CurrentUserDependency,
) -> ExplainResponse:
    """Explain an SBS regulation concept using RAG-grounded context."""
    _ = current_user
    result = await use_case.execute(
        ExplainConceptRequest(
            question=request.question,
            top_k=request.top_k,
        )
    )
    return _to_response(result)


def _to_response(result: ExplainConceptResult) -> ExplainResponse:
    return ExplainResponse(
        type="text",
        data=ExplainDataResponse(
            answer=result.answer,
            citations=[
                CitationResponse(
                    chunk_id=citation.chunk_id,
                    label=citation.label,
                    text_preview=citation.text_preview,
                )
                for citation in result.citations
            ],
        ),
    )
