"""Generate Vertex AI embeddings for chunks stored in PostgreSQL."""

# ruff: noqa: E402

import argparse
import asyncio
import sys
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sbs_assistant.config.settings import Settings
from sbs_assistant.infrastructure.embeddings.vertex_embeddings import VertexEmbeddings
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Regenerate embeddings for every chunk, including existing vectors.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of chunks to embed in this run.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = Settings()
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required to generate embeddings")

    embeddings = VertexEmbeddings(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.embeddings_model,
    )
    pool = await create_pool(settings)
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                _select_chunks_sql(include_existing=args.all, limit=args.limit)
            )
            total = len(rows)
            for index, row in enumerate(rows, start=1):
                vector = await embeddings.embed_document(row["texto"])
                await connection.execute(
                    "UPDATE chunks SET embedding = $1::vector WHERE id = $2",
                    _format_embedding(vector),
                    row["id"],
                )
                print(f"[{index}/{total}] embedded {row['id']}")
        print(f"Embedding completed: {total} chunks updated")
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


def _select_chunks_sql(include_existing: bool, limit: int | None) -> str:
    where_clause = "" if include_existing else "WHERE embedding IS NULL"
    limit_clause = "" if limit is None else f"LIMIT {limit}"
    return f"""
        SELECT id, texto
        FROM chunks
        {where_clause}
        ORDER BY id
        {limit_clause}
        """


def _format_embedding(embedding: Iterable[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


if __name__ == "__main__":
    asyncio.run(main())
