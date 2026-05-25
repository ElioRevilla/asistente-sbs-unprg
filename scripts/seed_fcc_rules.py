"""Seed curated SBS credit conversion factors into PostgreSQL."""

# ruff: noqa: E402

import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sbs_assistant.config.settings import Settings
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)

SEED_PATH = PROJECT_ROOT / "data" / "fcc_rules_seed.csv"


async def main() -> None:
    with SEED_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    pool = await create_pool(Settings())
    try:
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("TRUNCATE TABLE fcc_rules RESTART IDENTITY")
                await connection.executemany(
                    """
                    INSERT INTO fcc_rules (
                      codigo,
                      descripcion,
                      factor_conversion,
                      articulo_fuente
                    )
                    VALUES ($1, $2, $3, $4)
                    """,
                    [
                        (
                            row["codigo"],
                            row["descripcion"],
                            Decimal(row["factor_conversion"]),
                            row["articulo_fuente"],
                        )
                        for row in rows
                    ],
                )
        print(f"Seeded {len(rows)} FCC rules from {SEED_PATH}")
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


if __name__ == "__main__":
    asyncio.run(main())
