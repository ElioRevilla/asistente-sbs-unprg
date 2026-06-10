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
