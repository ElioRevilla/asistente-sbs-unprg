from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.persistence.connection import get_pool
from sbs_assistant.infrastructure.persistence.postgres_teacher_analytics_repo import (
    CategoryPerformance,
    ConceptMetric,
    ConfusionMetric,
    PostgresTeacherAnalyticsRepository,
    StudentConceptMastery,
    TeacherConceptAnalytics,
    TeacherOverview,
    TeacherStudentAnalytics,
    TeacherStudentSummary,
    TimelinePoint,
)

router = APIRouter(prefix="/teacher", tags=["teacher"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUserDependency = Annotated[FirebaseUser | None, Depends(get_current_user)]


class TeacherOverviewResponse(BaseModel):
    """Base metrics shown in the teacher dashboard."""

    active_students: int
    total_conversations: int
    completed_simulations: int
    average_simulation_score: float | None
    explain_questions: int
    explain_answers: int
    example_cases_answered: int


class TeacherStudentSummaryResponse(BaseModel):
    """Student row shown in the teacher dashboard."""

    student_id: str
    conversations: int
    completed_simulations: int
    average_simulation_score: float | None
    example_attempts: int
    last_activity: str | None


class TeacherStudentsResponse(BaseModel):
    """Collection of student summary rows."""

    students: list[TeacherStudentSummaryResponse]


class StudentConceptMasteryResponse(BaseModel):
    """Student mastery metric for a concept."""

    concept: str
    mastery_score: float
    attempts: int
    last_answer_correct: bool | None
    updated_at: str | None


class CategoryPerformanceResponse(BaseModel):
    """Correctness by category."""

    category: str
    correct: int
    incorrect: int
    accuracy: float | None


class ConfusionMetricResponse(BaseModel):
    """Frequent category confusion."""

    expected_category: str
    selected_category: str
    count: int


class TimelinePointResponse(BaseModel):
    """Temporal activity point for a student."""

    period: str
    example_attempts: int
    completed_simulations: int
    average_simulation_score: float | None


class TeacherStudentAnalyticsResponse(BaseModel):
    """Detailed learning analytics for a student."""

    student_id: str
    mastery_by_concept: list[StudentConceptMasteryResponse]
    category_performance: list[CategoryPerformanceResponse]
    confusions: list[ConfusionMetricResponse]
    timeline: list[TimelinePointResponse]


class ConceptMetricResponse(BaseModel):
    """Aggregated concept metric."""

    concept: str
    attempts: int
    errors: int
    average_mastery: float | None


class TeacherConceptAnalyticsResponse(BaseModel):
    """Concept ranking metrics."""

    most_consulted: list[ConceptMetricResponse]
    most_errors: list[ConceptMetricResponse]


async def get_teacher_analytics_repository(
    settings: SettingsDependency,
) -> PostgresTeacherAnalyticsRepository:
    """Build the teacher analytics repository for API requests."""
    pool = await get_pool(settings)
    return PostgresTeacherAnalyticsRepository(pool=pool)


@router.get("/overview", response_model=TeacherOverviewResponse)
async def teacher_overview(
    repository: Annotated[
        PostgresTeacherAnalyticsRepository,
        Depends(get_teacher_analytics_repository),
    ],
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> TeacherOverviewResponse:
    """Return base learning analytics for allowed teacher accounts."""
    _require_teacher(current_user, settings)
    return _overview_response(await repository.overview())


@router.get("/students", response_model=TeacherStudentsResponse)
async def teacher_students(
    repository: Annotated[
        PostgresTeacherAnalyticsRepository,
        Depends(get_teacher_analytics_repository),
    ],
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> TeacherStudentsResponse:
    """Return student rows for teacher analytics."""
    _require_teacher(current_user, settings)
    return TeacherStudentsResponse(
        students=[_student_summary_response(row) for row in await repository.students()]
    )


@router.get(
    "/students/{student_id}/analytics", response_model=TeacherStudentAnalyticsResponse
)
async def teacher_student_analytics(
    student_id: str,
    repository: Annotated[
        PostgresTeacherAnalyticsRepository,
        Depends(get_teacher_analytics_repository),
    ],
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> TeacherStudentAnalyticsResponse:
    """Return detailed analytics for a selected student."""
    _require_teacher(current_user, settings)
    return _student_analytics_response(await repository.student_analytics(student_id))


@router.get("/concepts", response_model=TeacherConceptAnalyticsResponse)
async def teacher_concepts(
    repository: Annotated[
        PostgresTeacherAnalyticsRepository,
        Depends(get_teacher_analytics_repository),
    ],
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> TeacherConceptAnalyticsResponse:
    """Return concept-level rankings."""
    _require_teacher(current_user, settings)
    return _concept_analytics_response(await repository.concepts())


def _require_teacher(current_user: FirebaseUser | None, settings: Settings) -> None:
    if current_user is None:
        if settings.firebase_auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase authentication is required.",
            )
        return

    allowed_emails = {email.lower() for email in settings.teacher_allowed_emails}
    user_email = (current_user.email or "").lower()
    if user_email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access is not allowed for this account.",
        )


def _overview_response(overview: TeacherOverview) -> TeacherOverviewResponse:
    return TeacherOverviewResponse(
        active_students=overview.active_students,
        total_conversations=overview.total_conversations,
        completed_simulations=overview.completed_simulations,
        average_simulation_score=overview.average_simulation_score,
        explain_questions=overview.explain_questions,
        explain_answers=overview.explain_answers,
        example_cases_answered=overview.example_cases_answered,
    )


def _student_summary_response(
    student: TeacherStudentSummary,
) -> TeacherStudentSummaryResponse:
    return TeacherStudentSummaryResponse(
        student_id=student.student_id,
        conversations=student.conversations,
        completed_simulations=student.completed_simulations,
        average_simulation_score=student.average_simulation_score,
        example_attempts=student.example_attempts,
        last_activity=student.last_activity,
    )


def _student_analytics_response(
    analytics: TeacherStudentAnalytics,
) -> TeacherStudentAnalyticsResponse:
    return TeacherStudentAnalyticsResponse(
        student_id=analytics.student_id,
        mastery_by_concept=[
            _mastery_response(row) for row in analytics.mastery_by_concept
        ],
        category_performance=[
            _category_response(row) for row in analytics.category_performance
        ],
        confusions=[_confusion_response(row) for row in analytics.confusions],
        timeline=[_timeline_response(row) for row in analytics.timeline],
    )


def _concept_analytics_response(
    analytics: TeacherConceptAnalytics,
) -> TeacherConceptAnalyticsResponse:
    return TeacherConceptAnalyticsResponse(
        most_consulted=[
            _concept_metric_response(row) for row in analytics.most_consulted
        ],
        most_errors=[_concept_metric_response(row) for row in analytics.most_errors],
    )


def _mastery_response(
    mastery: StudentConceptMastery,
) -> StudentConceptMasteryResponse:
    return StudentConceptMasteryResponse(
        concept=mastery.concept,
        mastery_score=mastery.mastery_score,
        attempts=mastery.attempts,
        last_answer_correct=mastery.last_answer_correct,
        updated_at=mastery.updated_at,
    )


def _category_response(
    performance: CategoryPerformance,
) -> CategoryPerformanceResponse:
    return CategoryPerformanceResponse(
        category=performance.category,
        correct=performance.correct,
        incorrect=performance.incorrect,
        accuracy=performance.accuracy,
    )


def _confusion_response(confusion: ConfusionMetric) -> ConfusionMetricResponse:
    return ConfusionMetricResponse(
        expected_category=confusion.expected_category,
        selected_category=confusion.selected_category,
        count=confusion.count,
    )


def _timeline_response(point: TimelinePoint) -> TimelinePointResponse:
    return TimelinePointResponse(
        period=point.period,
        example_attempts=point.example_attempts,
        completed_simulations=point.completed_simulations,
        average_simulation_score=point.average_simulation_score,
    )


def _concept_metric_response(metric: ConceptMetric) -> ConceptMetricResponse:
    return ConceptMetricResponse(
        concept=metric.concept,
        attempts=metric.attempts,
        errors=metric.errors,
        average_mastery=metric.average_mastery,
    )
