from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.schemas.request_schemas import (
    GenerateExampleRequestSchema,
    ValidateExampleAnswerRequestSchema,
)
from sbs_assistant.api.schemas.response_schemas import (
    ExampleDataResponse,
    ExampleFeedbackDataResponse,
    ExampleFeedbackResponse,
    ExampleResponse,
)
from sbs_assistant.application.services.llm_example_variation import (
    LLMExampleCaseVariationService,
)
from sbs_assistant.application.use_cases.generate_example import (
    GenerateExampleRequest,
    GenerateExampleResult,
    GenerateExampleUseCase,
)
from sbs_assistant.application.use_cases.validate_example_answer import (
    ValidateExampleAnswerRequest,
    ValidateExampleAnswerResult,
    ValidateExampleAnswerUseCase,
)
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.llm.vertex_gemini_client import VertexGeminiClient
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)
from sbs_assistant.infrastructure.persistence.postgres_synthetic_case_repo import (
    PostgresSyntheticCaseRepository,
)

router = APIRouter(prefix="/modes/example", tags=["modes"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUserDependency = Annotated[FirebaseUser | None, Depends(get_current_user)]


async def get_example_repository(
    settings: SettingsDependency,
) -> AsyncIterator[PostgresSyntheticCaseRepository]:
    """Build the synthetic case repository for API requests."""
    pool = await create_pool(settings)
    try:
        yield PostgresSyntheticCaseRepository(pool=pool)
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


@router.post("/generate", response_model=ExampleResponse)
async def generate_example(
    request: GenerateExampleRequestSchema,
    repository: Annotated[
        PostgresSyntheticCaseRepository,
        Depends(get_example_repository),
    ],
    current_user: CurrentUserDependency,
) -> ExampleResponse:
    """Generate an auditable synthetic debtor case."""
    _ = current_user
    use_case = GenerateExampleUseCase(
        repository=repository,
        variation_service=_variation_service(request.use_llm_variation),
    )
    result = await use_case.execute(
        GenerateExampleRequest(
            concept=request.concept,
            use_llm_variation=request.use_llm_variation,
        )
    )
    return _to_example_response(result)


@router.post("/answer", response_model=ExampleFeedbackResponse)
async def answer_example(
    request: ValidateExampleAnswerRequestSchema,
    repository: Annotated[
        PostgresSyntheticCaseRepository,
        Depends(get_example_repository),
    ],
    current_user: CurrentUserDependency,
) -> ExampleFeedbackResponse:
    """Validate a student's answer to an example case."""
    _ = current_user
    use_case = ValidateExampleAnswerUseCase(repository=repository)
    try:
        result = await use_case.execute(
            ValidateExampleAnswerRequest(
                case_id=UUID(request.case_id),
                selected_category=request.selected_category,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _to_feedback_response(result)


def _to_example_response(result: GenerateExampleResult) -> ExampleResponse:
    return ExampleResponse(
        type="example",
        data=ExampleDataResponse(
            case_id=str(result.case_id),
            concept=result.concept,
            case=result.case_data,
            options=result.options,
            source_article=result.source_article,
        ),
    )


def _variation_service(enabled: bool) -> LLMExampleCaseVariationService | None:
    if not enabled:
        return None
    settings = get_settings()
    if not settings.gcp_project_id:
        raise HTTPException(
            status_code=503,
            detail="GCP_PROJECT_ID is required to use LLM case variation.",
        )
    llm = VertexGeminiClient(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.gemini_flash_model,
    )
    return LLMExampleCaseVariationService(llm=llm)


def _to_feedback_response(
    result: ValidateExampleAnswerResult,
) -> ExampleFeedbackResponse:
    return ExampleFeedbackResponse(
        type="example_feedback",
        data=ExampleFeedbackDataResponse(
            correct=result.correct,
            correct_category=result.correct_category,
            feedback=result.feedback,
            source_article=result.source_article,
        ),
    )
