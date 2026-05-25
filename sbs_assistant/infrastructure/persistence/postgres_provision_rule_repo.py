import asyncpg

from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


class PostgresProvisionRuleRepository:
    """Persist structured provisioning rules in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "TRUNCATE TABLE provision_rules RESTART IDENTITY"
                )
                if not rules:
                    return
                await connection.executemany(
                    """
                    INSERT INTO provision_rules (
                      categoria,
                      tipo_credito,
                      tipo_garantia,
                      porcentaje_provision,
                      articulo_fuente
                    )
                    VALUES ($1, $2, $3, $4, $5);
                    """,
                    [
                        (
                            rule.category.value,
                            rule.credit_type.value,
                            rule.guarantee_type,
                            rule.provision_percentage,
                            rule.source_article,
                        )
                        for rule in rules
                    ],
                )

    async def find_percentage(
        self,
        category: str,
        credit_type: str,
        guarantee_type: str,
    ) -> ProvisionRule | None:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT
                  categoria,
                  tipo_credito,
                  tipo_garantia,
                  porcentaje_provision,
                  articulo_fuente
                FROM provision_rules
                WHERE categoria = $1
                  AND tipo_garantia = $2
                  AND tipo_credito IN ($3, 'todos')
                ORDER BY CASE WHEN tipo_credito = $3 THEN 0 ELSE 1 END
                LIMIT 1
                """,
                category,
                guarantee_type,
                credit_type,
            )
        if row is None:
            return None
        return ProvisionRule(
            category=self._coerce_category(row["categoria"]),
            credit_type=self._coerce_credit_type(row["tipo_credito"]),
            guarantee_type=row["tipo_garantia"],
            provision_percentage=row["porcentaje_provision"],
            source_article=row["articulo_fuente"],
        )

    def _coerce_category(self, value: str) -> Category:
        for category in Category:
            if category.value == value:
                return category
        raise ValueError(f"Unsupported category from database: {value}")

    def _coerce_credit_type(self, value: str) -> CreditType:
        for credit_type in CreditType:
            if credit_type.value == value:
                return credit_type
        return CreditType.CONSUMO
