from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True, slots=True)
class TeacherOverview:
    """Aggregated learning analytics for the teacher dashboard."""

    active_students: int
    total_conversations: int
    completed_simulations: int
    average_simulation_score: float | None
    explain_questions: int
    explain_answers: int
    example_cases_answered: int


@dataclass(frozen=True, slots=True)
class TeacherStudentSummary:
    """Per-student summary for teacher analytics."""

    student_id: str
    conversations: int
    completed_simulations: int
    average_simulation_score: float | None
    example_attempts: int
    last_activity: str | None


@dataclass(frozen=True, slots=True)
class StudentConceptMastery:
    """Mastery row for a student and concept."""

    concept: str
    mastery_score: float
    attempts: int
    last_answer_correct: bool | None
    updated_at: str | None


@dataclass(frozen=True, slots=True)
class CategoryPerformance:
    """Correctness by final expected category."""

    category: str
    correct: int
    incorrect: int
    accuracy: float | None


@dataclass(frozen=True, slots=True)
class ConfusionMetric:
    """Observed confusion between expected and selected categories."""

    expected_category: str
    selected_category: str
    count: int


@dataclass(frozen=True, slots=True)
class TimelinePoint:
    """Simple temporal learning activity point."""

    period: str
    example_attempts: int
    completed_simulations: int
    average_simulation_score: float | None


@dataclass(frozen=True, slots=True)
class TeacherStudentAnalytics:
    """Detailed analytics for a single student."""

    student_id: str
    mastery_by_concept: list[StudentConceptMastery]
    category_performance: list[CategoryPerformance]
    confusions: list[ConfusionMetric]
    timeline: list[TimelinePoint]


@dataclass(frozen=True, slots=True)
class ConceptMetric:
    """Aggregated metric for a concept."""

    concept: str
    attempts: int
    errors: int
    average_mastery: float | None


@dataclass(frozen=True, slots=True)
class TeacherConceptAnalytics:
    """Concept-level rankings for teacher analytics."""

    most_consulted: list[ConceptMetric]
    most_errors: list[ConceptMetric]


class PostgresTeacherAnalyticsRepository:
    """Read-only analytics queries for teacher-facing dashboards."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def overview(self) -> TeacherOverview:
        """Return the base dashboard metrics."""
        row = await self._pool.fetchrow("""
            WITH active_users AS (
              SELECT firebase_uid AS user_id
              FROM chat_conversations
              UNION
              SELECT user_id
              FROM simulation_sessions
              UNION
              SELECT student_key AS user_id
              FROM example_mastery
            ),
            explain_messages AS (
              SELECT
                message ->> 'role' AS role
              FROM chat_conversations,
              LATERAL jsonb_array_elements(messages) AS message
              WHERE mode = 'explicame'
            )
            SELECT
              (SELECT COUNT(*) FROM active_users) AS active_students,
              (SELECT COUNT(*) FROM chat_conversations) AS total_conversations,
              (
                SELECT COUNT(*)
                FROM simulation_sessions
                WHERE state = 'closed'
              ) AS completed_simulations,
              (
                SELECT AVG((verdict ->> 'overall')::float)
                FROM simulation_sessions
                WHERE state = 'closed' AND verdict IS NOT NULL
              ) AS average_simulation_score,
              (
                SELECT COUNT(*)
                FROM explain_messages
                WHERE role = 'user'
              ) AS explain_questions,
              (
                SELECT COUNT(*)
                FROM explain_messages
                WHERE role = 'assistant'
              ) AS explain_answers,
              (
                SELECT COALESCE(SUM(attempts), 0)
                FROM example_mastery
              ) AS example_cases_answered
            """)
        return TeacherOverview(
            active_students=int(row["active_students"] or 0),
            total_conversations=int(row["total_conversations"] or 0),
            completed_simulations=int(row["completed_simulations"] or 0),
            average_simulation_score=(
                float(row["average_simulation_score"])
                if row["average_simulation_score"] is not None
                else None
            ),
            explain_questions=int(row["explain_questions"] or 0),
            explain_answers=int(row["explain_answers"] or 0),
            example_cases_answered=int(row["example_cases_answered"] or 0),
        )

    async def students(self) -> list[TeacherStudentSummary]:
        """Return per-student summary metrics."""
        rows = await self._pool.fetch("""
            WITH users AS (
              SELECT firebase_uid AS student_id FROM chat_conversations
              UNION
              SELECT user_id AS student_id FROM simulation_sessions
              UNION
              SELECT student_key AS student_id FROM example_mastery
            ),
            conversation_stats AS (
              SELECT
                firebase_uid AS student_id,
                COUNT(*) AS conversations,
                MAX(updated_at) AS last_activity
              FROM chat_conversations
              GROUP BY firebase_uid
            ),
            simulation_stats AS (
              SELECT
                user_id AS student_id,
                COUNT(*) FILTER (WHERE state = 'closed') AS completed_simulations,
                AVG((verdict ->> 'overall')::float) FILTER (
                  WHERE state = 'closed' AND verdict IS NOT NULL
                ) AS average_simulation_score,
                MAX(updated_at) AS last_activity
              FROM simulation_sessions
              GROUP BY user_id
            ),
            example_stats AS (
              SELECT
                student_key AS student_id,
                COALESCE(SUM(attempts), 0) AS example_attempts,
                MAX(updated_at) AS last_activity
              FROM example_mastery
              GROUP BY student_key
            )
            SELECT
              users.student_id,
              COALESCE(conversation_stats.conversations, 0) AS conversations,
              COALESCE(simulation_stats.completed_simulations, 0)
                AS completed_simulations,
              simulation_stats.average_simulation_score,
              COALESCE(example_stats.example_attempts, 0) AS example_attempts,
              GREATEST(
                COALESCE(conversation_stats.last_activity, '-infinity'::timestamptz),
                COALESCE(simulation_stats.last_activity, '-infinity'::timestamptz),
                COALESCE(example_stats.last_activity, '-infinity'::timestamptz)
              ) AS last_activity
            FROM users
            LEFT JOIN conversation_stats USING (student_id)
            LEFT JOIN simulation_stats USING (student_id)
            LEFT JOIN example_stats USING (student_id)
            ORDER BY last_activity DESC NULLS LAST, users.student_id
            """)
        return [
            TeacherStudentSummary(
                student_id=str(row["student_id"]),
                conversations=int(row["conversations"] or 0),
                completed_simulations=int(row["completed_simulations"] or 0),
                average_simulation_score=(
                    float(row["average_simulation_score"])
                    if row["average_simulation_score"] is not None
                    else None
                ),
                example_attempts=int(row["example_attempts"] or 0),
                last_activity=(
                    row["last_activity"].isoformat()
                    if row["last_activity"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    async def student_analytics(self, student_id: str) -> TeacherStudentAnalytics:
        """Return detailed analytics for a single student."""
        mastery_rows = await self._pool.fetch(
            """
            SELECT concept, mastery_score, attempts, last_answer_correct, updated_at
            FROM example_mastery
            WHERE student_key = $1
            ORDER BY mastery_score ASC, attempts DESC, concept
            """,
            student_id,
        )
        category_rows = await self._pool.fetch(
            """
            SELECT
              "case" -> 'ground_truth' ->> 'category' AS category,
              COUNT(*) FILTER (
                WHERE classification ->> 'category'
                  = "case" -> 'ground_truth' ->> 'category'
              ) AS correct,
              COUNT(*) FILTER (
                WHERE classification ->> 'category'
                  <> "case" -> 'ground_truth' ->> 'category'
              ) AS incorrect
            FROM simulation_sessions
            WHERE user_id = $1
              AND state = 'closed'
              AND classification IS NOT NULL
            GROUP BY category
            ORDER BY category
            """,
            student_id,
        )
        confusion_rows = await self._pool.fetch(
            """
            SELECT
              "case" -> 'ground_truth' ->> 'category' AS expected_category,
              classification ->> 'category' AS selected_category,
              COUNT(*) AS count
            FROM simulation_sessions
            WHERE user_id = $1
              AND state = 'closed'
              AND classification IS NOT NULL
              AND classification ->> 'category'
                <> "case" -> 'ground_truth' ->> 'category'
            GROUP BY expected_category, selected_category
            ORDER BY count DESC, expected_category, selected_category
            LIMIT 10
            """,
            student_id,
        )
        timeline_rows = await self._pool.fetch(
            """
            WITH example_timeline AS (
              SELECT
                date_trunc('day', updated_at)::date AS period,
                COALESCE(SUM(attempts), 0) AS example_attempts,
                0 AS completed_simulations,
                NULL::float AS average_simulation_score
              FROM example_mastery
              WHERE student_key = $1
              GROUP BY period
            ),
            simulation_timeline AS (
              SELECT
                date_trunc('day', updated_at)::date AS period,
                0 AS example_attempts,
                COUNT(*) FILTER (WHERE state = 'closed') AS completed_simulations,
                AVG((verdict ->> 'overall')::float) FILTER (
                  WHERE state = 'closed' AND verdict IS NOT NULL
                ) AS average_simulation_score
              FROM simulation_sessions
              WHERE user_id = $1
              GROUP BY period
            )
            SELECT
              period,
              SUM(example_attempts) AS example_attempts,
              SUM(completed_simulations) AS completed_simulations,
              AVG(average_simulation_score) FILTER (
                WHERE average_simulation_score IS NOT NULL
              ) AS average_simulation_score
            FROM (
              SELECT * FROM example_timeline
              UNION ALL
              SELECT * FROM simulation_timeline
            ) timeline
            GROUP BY period
            ORDER BY period
            """,
            student_id,
        )
        return TeacherStudentAnalytics(
            student_id=student_id,
            mastery_by_concept=[
                StudentConceptMastery(
                    concept=str(row["concept"]),
                    mastery_score=float(row["mastery_score"]),
                    attempts=int(row["attempts"] or 0),
                    last_answer_correct=row["last_answer_correct"],
                    updated_at=(
                        row["updated_at"].isoformat()
                        if row["updated_at"] is not None
                        else None
                    ),
                )
                for row in mastery_rows
            ],
            category_performance=[_category_performance(row) for row in category_rows],
            confusions=[
                ConfusionMetric(
                    expected_category=str(row["expected_category"]),
                    selected_category=str(row["selected_category"]),
                    count=int(row["count"] or 0),
                )
                for row in confusion_rows
            ],
            timeline=[
                TimelinePoint(
                    period=row["period"].isoformat(),
                    example_attempts=int(row["example_attempts"] or 0),
                    completed_simulations=int(row["completed_simulations"] or 0),
                    average_simulation_score=(
                        float(row["average_simulation_score"])
                        if row["average_simulation_score"] is not None
                        else None
                    ),
                )
                for row in timeline_rows
            ],
        )

    async def concepts(self) -> TeacherConceptAnalytics:
        """Return concept-level rankings."""
        rows = await self._pool.fetch("""
            SELECT
              concept,
              COALESCE(SUM(attempts), 0) AS attempts,
              COUNT(*) FILTER (WHERE last_answer_correct = false) AS errors,
              AVG(mastery_score) AS average_mastery
            FROM example_mastery
            GROUP BY concept
            ORDER BY attempts DESC, concept
            """)
        concepts = [
            ConceptMetric(
                concept=str(row["concept"]),
                attempts=int(row["attempts"] or 0),
                errors=int(row["errors"] or 0),
                average_mastery=(
                    float(row["average_mastery"])
                    if row["average_mastery"] is not None
                    else None
                ),
            )
            for row in rows
        ]
        return TeacherConceptAnalytics(
            most_consulted=concepts[:10],
            most_errors=sorted(
                concepts,
                key=lambda concept: (-concept.errors, concept.concept),
            )[:10],
        )


def _category_performance(row: asyncpg.Record) -> CategoryPerformance:
    correct = int(row["correct"] or 0)
    incorrect = int(row["incorrect"] or 0)
    total = correct + incorrect
    return CategoryPerformance(
        category=str(row["category"]),
        correct=correct,
        incorrect=incorrect,
        accuracy=(correct / total if total else None),
    )
