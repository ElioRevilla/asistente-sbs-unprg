"""Print ingestion counts from PostgreSQL."""

# ruff: noqa: E402

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sbs_assistant.config.settings import Settings
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)


async def main() -> None:
    pool = await create_pool(Settings())
    try:
        async with pool.acquire() as connection:
            chunks_count = await connection.fetchval("SELECT COUNT(*) FROM chunks")
            embedded_chunks_count = await connection.fetchval(
                "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL"
            )
            rules_count = await connection.fetchval(
                "SELECT COUNT(*) FROM provision_rules"
            )
            fcc_count = await connection.fetchval("SELECT COUNT(*) FROM fcc_rules")
            rows = await connection.fetch("""
                SELECT id, numeral, LEFT(texto, 80) AS text
                FROM chunks
                ORDER BY id
                LIMIT 5
                """)
            print(f"chunks={chunks_count}")
            print(f"chunks_with_embeddings={embedded_chunks_count}")
            print(f"provision_rules={rules_count}")
            print(f"fcc_rules={fcc_count}")
            for row in rows:
                print(dict(row))
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


if __name__ == "__main__":
    asyncio.run(main())
