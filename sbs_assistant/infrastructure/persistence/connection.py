import asyncio

import asyncpg
from google.cloud.sql.connector import Connector, IPTypes

from sbs_assistant.config.settings import Settings

_CONNECTORS: list[Connector] = []
_POOL: asyncpg.Pool | None = None
_POOL_LOCK: asyncio.Lock | None = None


def _required(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


async def create_pool(settings: Settings) -> asyncpg.Pool:
    """Create an asyncpg pool for Cloud SQL/PostgreSQL."""
    if settings.cloudsql_instance_connection_name:
        connector = Connector(loop=asyncio.get_running_loop())
        _CONNECTORS.append(connector)

        async def connect(*args: object, **kwargs: object) -> asyncpg.Connection:
            return await connector.connect_async(
                settings.cloudsql_instance_connection_name,
                "asyncpg",
                user=_required(settings.postgres_user, "DB_USER"),
                password=_required(settings.postgres_password, "DB_PASSWORD"),
                db=_required(settings.postgres_database, "DB_NAME"),
                ip_type=IPTypes.PUBLIC,
            )

        return await asyncpg.create_pool(
            min_size=1,
            max_size=5,
            connect=connect,
        )

    return await asyncpg.create_pool(
        host=_required(settings.postgres_host, "DB_HOST"),
        port=settings.postgres_port,
        database=_required(settings.postgres_database, "DB_NAME"),
        user=_required(settings.postgres_user, "DB_USER"),
        password=_required(settings.postgres_password, "DB_PASSWORD"),
    )


async def get_pool(settings: Settings) -> asyncpg.Pool:
    """Return a process-wide pool for API requests."""
    global _POOL, _POOL_LOCK
    if _POOL is not None and not _POOL._closed:  # noqa: SLF001
        return _POOL

    if _POOL_LOCK is None:
        _POOL_LOCK = asyncio.Lock()

    async with _POOL_LOCK:
        if _POOL is None or _POOL._closed:  # noqa: SLF001
            _POOL = await create_pool(settings)
    return _POOL


async def close_pool() -> None:
    """Close the process-wide database pool and Cloud SQL connectors."""
    global _POOL
    if _POOL is not None and not _POOL._closed:  # noqa: SLF001
        await _POOL.close()
    _POOL = None
    await close_cloud_sql_connectors()


async def close_cloud_sql_connectors() -> None:
    """Close Cloud SQL connector sessions created by this process."""
    while _CONNECTORS:
        connector = _CONNECTORS.pop()
        await connector.close_async()
