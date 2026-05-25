"""Run raw SQL migrations against PostgreSQL."""

# ruff: noqa: E402

import asyncio
import sys
from pathlib import Path

import asyncpg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sbs_assistant.config.settings import Settings
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _required(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is required to run database migrations")
    return value


async def _ensure_migrations_table(connection: asyncpg.Connection) -> None:
    await connection.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          applied_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)


async def _has_migration(connection: asyncpg.Connection, version: str) -> bool:
    result = await connection.fetchval(
        "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = $1)",
        version,
    )
    return bool(result)


async def _run_migration(connection: asyncpg.Connection, path: Path) -> None:
    version = path.name
    if await _has_migration(connection, version):
        print(f"Skipping {version}")
        return

    async with connection.transaction():
        await connection.execute(path.read_text(encoding="utf-8"))
        await connection.execute(
            "INSERT INTO schema_migrations(version) VALUES ($1)",
            version,
        )
    print(f"Applied {version}")


async def main() -> None:
    settings = Settings()
    _required(settings.postgres_database, "DB_NAME")
    _required(settings.postgres_user, "DB_USER")
    _required(settings.postgres_password, "DB_PASSWORD")
    pool = await create_pool(settings)

    try:
        async with pool.acquire() as connection:
            await _ensure_migrations_table(connection)
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                await _run_migration(connection, migration)
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


if __name__ == "__main__":
    asyncio.run(main())
