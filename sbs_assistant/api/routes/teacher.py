from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.config.settings import Settings, get_settings
from sbs_assistant.infrastructure.persistence.connection import get_pool
from sbs_assistant.infrastructure.persistence.postgres_teacher_analytics_repo import (
    PostgresTeacherAnalyticsRepository,
    TeacherOverview,
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
    return _to_response(await repository.overview())


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


def _to_response(overview: TeacherOverview) -> TeacherOverviewResponse:
    return TeacherOverviewResponse(
        active_students=overview.active_students,
        total_conversations=overview.total_conversations,
        completed_simulations=overview.completed_simulations,
        average_simulation_score=overview.average_simulation_score,
        explain_questions=overview.explain_questions,
        explain_answers=overview.explain_answers,
        example_cases_answered=overview.example_cases_answered,
    )
