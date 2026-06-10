from fastapi.testclient import TestClient

from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.api.main import app
from sbs_assistant.api.routes.teacher import get_teacher_analytics_repository
from sbs_assistant.infrastructure.persistence.postgres_teacher_analytics_repo import (
    CategoryPerformance,
    ConceptMetric,
    ConfusionMetric,
    StudentConceptMastery,
    TeacherConceptAnalytics,
    TeacherOverview,
    TeacherStudentAnalytics,
    TeacherStudentSummary,
    TimelinePoint,
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

    async def students(self) -> list[TeacherStudentSummary]:
        return [
            TeacherStudentSummary(
                student_id="student-1",
                conversations=3,
                completed_simulations=2,
                average_simulation_score=0.9,
                example_attempts=5,
                last_activity="2026-06-09T12:30:00+00:00",
            )
        ]

    async def student_analytics(self, student_id: str) -> TeacherStudentAnalytics:
        return TeacherStudentAnalytics(
            student_id=student_id,
            mastery_by_concept=[
                StudentConceptMastery(
                    concept="categoria_cpp_minorista",
                    mastery_score=0.72,
                    attempts=4,
                    last_answer_correct=True,
                    updated_at="2026-06-09T12:30:00+00:00",
                )
            ],
            category_performance=[
                CategoryPerformance(
                    category="CPP",
                    correct=2,
                    incorrect=1,
                    accuracy=2 / 3,
                )
            ],
            confusions=[
                ConfusionMetric(
                    expected_category="CPP",
                    selected_category="Deficiente",
                    count=1,
                )
            ],
            timeline=[
                TimelinePoint(
                    period="2026-06-09",
                    example_attempts=4,
                    completed_simulations=2,
                    average_simulation_score=0.9,
                )
            ],
        )

    async def concepts(self) -> TeacherConceptAnalytics:
        return TeacherConceptAnalytics(
            most_consulted=[
                ConceptMetric(
                    concept="categoria_cpp_minorista",
                    attempts=8,
                    errors=1,
                    average_mastery=0.72,
                )
            ],
            most_errors=[
                ConceptMetric(
                    concept="categoria_deficiente_minorista",
                    attempts=5,
                    errors=3,
                    average_mastery=0.44,
                )
            ],
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


def test_teacher_students_returns_student_rows() -> None:
    app.dependency_overrides[get_teacher_analytics_repository] = (
        lambda: FakeTeacherAnalyticsRepository()
    )
    app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
        uid="teacher-1",
        email="docente@sbs.test",
        name="Docente",
    )
    client = TestClient(app)

    response = client.get("/teacher/students")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["students"][0]["student_id"] == "student-1"
    assert response.json()["students"][0]["completed_simulations"] == 2


def test_teacher_student_analytics_returns_learning_metrics() -> None:
    app.dependency_overrides[get_teacher_analytics_repository] = (
        lambda: FakeTeacherAnalyticsRepository()
    )
    app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
        uid="teacher-1",
        email="docente@sbs.test",
        name="Docente",
    )
    client = TestClient(app)

    response = client.get("/teacher/students/student-1/analytics")

    app.dependency_overrides.clear()
    payload = response.json()
    assert response.status_code == 200
    assert payload["student_id"] == "student-1"
    assert payload["mastery_by_concept"][0]["concept"] == "categoria_cpp_minorista"
    assert payload["category_performance"][0]["category"] == "CPP"
    assert payload["confusions"][0]["selected_category"] == "Deficiente"
    assert payload["timeline"][0]["example_attempts"] == 4


def test_teacher_concepts_returns_rankings() -> None:
    app.dependency_overrides[get_teacher_analytics_repository] = (
        lambda: FakeTeacherAnalyticsRepository()
    )
    app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
        uid="teacher-1",
        email="docente@sbs.test",
        name="Docente",
    )
    client = TestClient(app)

    response = client.get("/teacher/concepts")

    app.dependency_overrides.clear()
    payload = response.json()
    assert response.status_code == 200
    assert payload["most_consulted"][0]["attempts"] == 8
    assert payload["most_errors"][0]["errors"] == 3
