"""Search SBS regulatory chunks with the PostgreSQL hybrid retriever."""

# ruff: noqa: E402

import argparse
import asyncio
import sys
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
from sbs_assistant.infrastructure.retrieval.postgres_hybrid_retriever import (
    PostgresHybridRetriever,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Question or search query in Spanish.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--tema", action="append", default=[])
    parser.add_argument("--tipo-contenido", default=None)
    parser.add_argument("--articulo", type=int, default=None)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = Settings()
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required to search with embeddings")

    pool = await create_pool(settings)
    try:
        retriever = PostgresHybridRetriever(
            pool=pool,
            embeddings=VertexEmbeddings(
                project_id=settings.gcp_project_id,
                location=settings.vertex_ai_location,
                model_name=settings.embeddings_model,
            ),
        )
        results = await retriever.retrieve_with_scores(
            args.query,
            top_k=args.top_k,
            filters=_filters_from_args(args),
        )
        for index, result in enumerate(results, start=1):
            chunk = result.chunk
            fragment = " ".join(chunk.text.split())[:280]
            print(
                f"{index}. id={chunk.id} numeral={chunk.numeral} "
                f"score={result.score:.6f}"
            )
            print(f"   {fragment}")
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


def _filters_from_args(args: argparse.Namespace) -> dict[str, object] | None:
    filters: dict[str, object] = {}
    if args.tema:
        filters["temas"] = args.tema
    if args.tipo_contenido:
        filters["tipo_contenido"] = args.tipo_contenido
    if args.articulo is not None:
        filters["articulo"] = args.articulo
    return filters or None


if __name__ == "__main__":
    asyncio.run(main())
