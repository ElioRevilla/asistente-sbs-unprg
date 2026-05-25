import json
from decimal import Decimal
from uuid import UUID

import asyncpg

from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType
from sbs_assistant.domain.value_objects.pedagogical_mode import PedagogicalMode


class PostgresSyntheticCaseRepository:
    """Persist synthetic cases in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, case: SyntheticCase) -> SyntheticCase:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO synthetic_cases (
                  tipo_credito,
                  descripcion_caso,
                  clasificacion_correcta,
                  provision_correcta,
                  articulo_fuente,
                  modo
                )
                VALUES ($1, $2::jsonb, $3, $4, $5, $6)
                RETURNING id
                """,
                case.credit_type.value,
                json.dumps(case.description),
                case.correct_category.value if case.correct_category else None,
                case.correct_provision,
                case.source_article,
                case.mode.value,
            )
        return SyntheticCase(
            id=row["id"],
            credit_type=case.credit_type,
            description=case.description,
            correct_category=case.correct_category,
            correct_provision=case.correct_provision,
            source_article=case.source_article,
            mode=case.mode,
        )

    async def get(self, case_id: UUID) -> SyntheticCase | None:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                  id,
                  tipo_credito,
                  descripcion_caso,
                  clasificacion_correcta,
                  provision_correcta,
                  articulo_fuente,
                  modo
                FROM synthetic_cases
                WHERE id = $1
                """,
                case_id,
            )
        if row is None:
            return None
        return SyntheticCase(
            id=row["id"],
            credit_type=self._credit_type(row["tipo_credito"]),
            description=self._description(row["descripcion_caso"]),
            correct_category=self._category(row["clasificacion_correcta"]),
            correct_provision=(
                Decimal(row["provision_correcta"])
                if row["provision_correcta"] is not None
                else None
            ),
            source_article=row["articulo_fuente"],
            mode=PedagogicalMode(row["modo"]),
        )

    def _category(self, value: str | None) -> Category | None:
        if value is None:
            return None
        for category in Category:
            if category.value == value:
                return category
        return None

    def _credit_type(self, value: str | None) -> CreditType:
        for credit_type in CreditType:
            if credit_type.value == value:
                return credit_type
        return CreditType.CONSUMO

    def _description(self, value: object) -> dict[str, object]:
        if isinstance(value, str):
            return dict(json.loads(value))
        if isinstance(value, dict):
            return value
        return {}
