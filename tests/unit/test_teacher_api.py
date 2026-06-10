from fastapi.testclient import TestClient

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.main import app
from sbs_assistant.api.routes.teacher import get_teacher_analytics_repository
from sbs_assistant.infrastructure.persistence.postgres_teacher_analytics_repo import (
    TeacherOverview,
)


class FakeTeacherAnalyticsRepository:
    async def overview(self) -> TeacherOverview:
        return TeacherOverview(
            active_students=3,
            total_conversations=8,
            completed_simulations=2,
            average_simulation_score=0.85,
            explain_questions=5,
            explain_answers=5,
            example_cases_answered=4,
        )


def test_teacher_overview_returns_metrics_for_allowed_teacher() -> None:
    app.dependency_overrides[get_teacher_analytics_repository] = (
        lambda: FakeTeacherAnalyticsRepository()
    )
    app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
        uid="teacher-1",
        email="docente@sbs.test",
        name="Docente",
    )
    client = TestClient(app)

    response = client.get("/teacher/overview")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "active_students": 3,
        "total_conversations": 8,
        "completed_simulations": 2,
        "average_simulation_score": 0.85,
        "explain_questions": 5,
        "explain_answers": 5,
        "example_cases_answered": 4,
    }


def test_teacher_overview_rejects_non_teacher_email() -> None:
    app.dependency_overrides[get_teacher_analytics_repository] = (
        lambda: FakeTeacherAnalyticsRepository()
    )
    app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
        uid="student-1",
        email="estudiante@sbs.test",
        name="Estudiante",
    )
    client = TestClient(app)

    response = client.get("/teacher/overview")

    app.dependency_overrides.clear()
    assert response.status_code == 403
