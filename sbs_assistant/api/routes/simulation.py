from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.schemas.request_schemas import (
    AdvanceSimulationTurnRequestSchema,
    StartSimulationRequestSchema,
    SubmitSimulationClassificationRequestSchema,
)
from sbs_assistant.api.schemas.response_schemas import (
    SimulationCaseResponse,
    SimulationClassificationResponse,
    SimulationDataResponse,
    SimulationResponse,
    SimulationTurnResponse,
    SimulationVerdictResponse,
)
from sbs_assistant.application.services.adversarial_judge import AdversarialJudge
from sbs_assistant.application.services.case_selector import (
    DeterministicSimulationCaseSelector,
)
from sbs_assistant.application.services.debate_orchestrator import (
    DebateOrchestrator,
    InvalidSimulationTransitionError,
)
from sbs_assistant.application.use_cases.advance_debate import (
    AdvanceDebateRequest,
    AdvanceDebateUseCase,
)
from sbs_assistant.application.use_cases.calculate_provision import (
    ProvisionCalculator,
)
from sbs_assistant.application.use_cases.get_simulation import (
    GetSimulationRequest,
    GetSimulationUseCase,
)
from sbs_assistant.application.use_cases.simulation_dtos import (
    ClassificationView,
    DebateTurnView,
    OperationCaseView,
    SimulationView,
    VerdictView,
)
from sbs_assistant.application.use_cases.start_simulation import (
    StartSimulationRequest,
    StartSimulationUseCase,
)
from sbs_assistant.application.use_cases.submit_classification import (
    SubmitClassificationRequest,
    SubmitClassificationUseCase,
)
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.embeddings.vertex_embeddings import VertexEmbeddings
from sbs_assistant.infrastructure.llm.gemini_agent_runner import GeminiAgentRunner
from sbs_assistant.infrastructure.llm.vertex_gemini_client import VertexGeminiClient
from sbs_assistant.infrastructure.persistence.connection import get_pool
from sbs_assistant.infrastructure.persistence.postgres_provision_rule_repo import (
    PostgresProvisionRuleRepository,
)
from sbs_assistant.infrastructure.persistence.postgres_simulation_repo import (
    PostgresSimulationRepository,
)
from sbs_assistant.infrastructure.retrieval.postgres_hybrid_retriever import (
    PostgresHybridRetriever,
)

router = APIRouter(prefix="/modes/simulation", tags=["modes"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUserDependency = Annotated[FirebaseUser | None, Depends(get_current_user)]


@dataclass(frozen=True, slots=True)
class SimulationDependencies:
    """Dependencies used by adversarial simulation endpoints."""

    repository: PostgresSimulationRepository
    orchestrator: DebateOrchestrator
    case_selector: DeterministicSimulationCaseSelector


async def get_simulation_dependencies(
    settings: SettingsDependency,
) -> SimulationDependencies:
    """Build simulation dependencies using existing infrastructure adapters."""
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required for Simulation mode")

    pool = await get_pool(settings)
    llm = VertexGeminiClient(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.gemini_flash_model,
    )
    agent_runner = GeminiAgentRunner(llm=llm)
    embeddings = VertexEmbeddings(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.embeddings_model,
    )
    retriever = PostgresHybridRetriever(pool=pool, embeddings=embeddings)
    provision_calculator = ProvisionCalculator(
        repository=PostgresProvisionRuleRepository(pool=pool)
    )
    judge = AdversarialJudge(rubric=agent_runner)
    return SimulationDependencies(
        repository=PostgresSimulationRepository(pool=pool),
        orchestrator=DebateOrchestrator(
            agents=agent_runner,
            judge=judge,
            retriever=retriever,
        ),
        case_selector=DeterministicSimulationCaseSelector(
            provision_calculator=provision_calculator,
        ),
    )


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(
    request: StartSimulationRequestSchema,
    dependencies: Annotated[
        SimulationDependencies,
        Depends(get_simulation_dependencies),
    ],
    current_user: CurrentUserDependency,
) -> SimulationResponse:
    """Start an adversarial simulation and show the client narrative."""
    use_case = StartSimulationUseCase(
        case_selector=dependencies.case_selector,
        repository=dependencies.repository,
        orchestrator=dependencies.orchestrator,
    )
    result = await use_case.execute(
        StartSimulationRequest(
            user_id=_user_id(current_user=current_user, student_id=request.student_id),
            focus=request.focus,
        )
    )
    return _to_simulation_response(result)


@router.post("/{session_id}/classify", response_model=SimulationResponse)
async def classify_simulation(
    session_id: UUID,
    request: SubmitSimulationClassificationRequestSchema,
    dependencies: Annotated[
        SimulationDependencies,
        Depends(get_simulation_dependencies),
    ],
    current_user: CurrentUserDependency,
) -> SimulationResponse:
    """Submit the student's initial classification."""
    _ = current_user
    use_case = SubmitClassificationUseCase(
        repository=dependencies.repository,
        orchestrator=dependencies.orchestrator,
    )
    try:
        result = await use_case.execute(
            SubmitClassificationRequest(
                session_id=session_id,
                category=request.category,
                justification=request.justification,
            )
        )
    except InvalidSimulationTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    return _to_simulation_response(result)


@router.post("/{session_id}/turn", response_model=SimulationResponse)
async def advance_simulation_turn(
    session_id: UUID,
    request: AdvanceSimulationTurnRequestSchema,
    dependencies: Annotated[
        SimulationDependencies,
        Depends(get_simulation_dependencies),
    ],
    current_user: CurrentUserDependency,
) -> SimulationResponse:
    """Advance the debate with the student's defense."""
    _ = current_user
    use_case = AdvanceDebateUseCase(
        repository=dependencies.repository,
        orchestrator=dependencies.orchestrator,
    )
    try:
        result = await use_case.execute(
            AdvanceDebateRequest(
                session_id=session_id,
                defense=request.defense,
            )
        )
    except InvalidSimulationTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return _to_simulation_response(result)


@router.get("/{session_id}", response_model=SimulationResponse)
async def get_simulation(
    session_id: UUID,
    dependencies: Annotated[
        SimulationDependencies,
        Depends(get_simulation_dependencies),
    ],
    current_user: CurrentUserDependency,
) -> SimulationResponse:
    """Return the current public view of an adversarial simulation."""
    _ = current_user
    use_case = GetSimulationUseCase(repository=dependencies.repository)
    try:
        result = await use_case.execute(GetSimulationRequest(session_id=session_id))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return _to_simulation_response(result)


def _to_simulation_response(view: SimulationView) -> SimulationResponse:
    return SimulationResponse(
        type="simulation",
        data=SimulationDataResponse(
            id=str(view.id),
            user_id=view.user_id,
            state=view.state,
            round=view.round,
            case=_case_response(view.case),
            classification=_classification_response(view.classification),
            transcript=[_turn_response(turn) for turn in view.transcript],
            verdict=_verdict_response(view.verdict),
            created_at=view.created_at.isoformat() if view.created_at else None,
            updated_at=view.updated_at.isoformat() if view.updated_at else None,
        ),
    )


def _case_response(view: OperationCaseView) -> SimulationCaseResponse:
    return SimulationCaseResponse(
        id=str(view.id),
        cartera_type=view.cartera_type,
        debtor_profile=view.debtor_profile,
        narrative_hints=view.narrative_hints,
        case_type=view.case_type,
        ground_truth=_classification_response(view.ground_truth),
        justifying_articles=view.justifying_articles,
    )


def _classification_response(
    view: ClassificationView | None,
) -> SimulationClassificationResponse | None:
    if view is None:
        return None
    return SimulationClassificationResponse(
        category=view.category,
        justification=view.justification,
    )


def _turn_response(view: DebateTurnView) -> SimulationTurnResponse:
    return SimulationTurnResponse(
        role=view.role,
        content=view.content,
        metadata=view.metadata,
        created_at=view.created_at.isoformat() if view.created_at else None,
    )


def _verdict_response(view: VerdictView | None) -> SimulationVerdictResponse | None:
    if view is None:
        return None
    return SimulationVerdictResponse(
        final_category=view.final_category,
        is_correct=view.is_correct,
        symbolic_score=view.symbolic_score,
        reasoning_score=view.reasoning_score,
        citation_score=view.citation_score,
        resisted_pressure=view.resisted_pressure,
        overall=view.overall,
        feedback=view.feedback,
    )


def _user_id(
    *,
    current_user: FirebaseUser | None,
    student_id: str | None,
) -> str:
    if current_user is not None:
        return current_user.uid
    if student_id and student_id.strip():
        return student_id.strip()
    return "local-simulation-user"
