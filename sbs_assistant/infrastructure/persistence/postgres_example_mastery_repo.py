import asyncpg

from sbs_assistant.domain.entities.example_mastery import ExampleMastery


class PostgresExampleMasteryRepository:
    """Persist adaptive Ejemplifica mastery in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, student_key: str, concept: str) -> ExampleMastery | None:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                  student_key,
                  concept,
                  mastery_score,
                  attempts,
                  last_answer_correct,
                  updated_at
                FROM example_mastery
                WHERE student_key = $1 AND concept = $2
                """,
                student_key,
                concept,
            )
        if row is None:
            return None
        return self._to_entity(row)

    async def list_by_student(self, student_key: str) -> list[ExampleMastery]:
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                  student_key,
                  concept,
                  mastery_score,
                  attempts,
                  last_answer_correct,
                  updated_at
                FROM example_mastery
                WHERE student_key = $1
                ORDER BY mastery_score ASC, updated_at ASC
                """,
                student_key,
            )
        return [self._to_entity(row) for row in rows]

    async def upsert(self, mastery: ExampleMastery) -> ExampleMastery:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO example_mastery (
                  student_key,
                  concept,
                  mastery_score,
                  attempts,
                  last_answer_correct
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (student_key, concept)
                DO UPDATE SET
                  mastery_score = EXCLUDED.mastery_score,
                  attempts = EXCLUDED.attempts,
                  last_answer_correct = EXCLUDED.last_answer_correct,
                  updated_at = NOW()
                RETURNING
                  student_key,
                  concept,
                  mastery_score,
                  attempts,
                  last_answer_correct,
                  updated_at
                """,
                mastery.student_key,
                mastery.concept,
                mastery.mastery_score,
                mastery.attempts,
                mastery.last_answer_correct,
            )
        return self._to_entity(row)

    def _to_entity(self, row: asyncpg.Record) -> ExampleMastery:
        return ExampleMastery(
            student_key=row["student_key"],
            concept=row["concept"],
            mastery_score=float(row["mastery_score"]),
            attempts=int(row["attempts"]),
            last_answer_correct=row["last_answer_correct"],
            updated_at=row["updated_at"],
        )
