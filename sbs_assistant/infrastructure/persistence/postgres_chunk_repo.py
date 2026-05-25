from collections.abc import Iterable

import asyncpg

from sbs_assistant.domain.entities.chunk import Chunk


class PostgresChunkRepository:
    """Persist regulatory chunks in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save_many(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        records = [
            (
                chunk.id,
                chunk.chapter,
                chunk.article,
                chunk.numeral,
                chunk.content_type,
                chunk.topics,
                chunk.text,
                chunk.cross_references,
                self._format_embedding(chunk.embedding),
            )
            for chunk in chunks
        ]

        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("TRUNCATE TABLE chunks")
                await connection.executemany(
                    """
                    INSERT INTO chunks (
                      id,
                      capitulo,
                      articulo,
                      numeral,
                      tipo_contenido,
                      temas,
                      texto,
                      referencias_cruzadas,
                      embedding
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector)
                    ON CONFLICT (id) DO UPDATE SET
                      capitulo = EXCLUDED.capitulo,
                      articulo = EXCLUDED.articulo,
                      numeral = EXCLUDED.numeral,
                      tipo_contenido = EXCLUDED.tipo_contenido,
                      temas = EXCLUDED.temas,
                      texto = EXCLUDED.texto,
                      referencias_cruzadas = EXCLUDED.referencias_cruzadas,
                      embedding = EXCLUDED.embedding;
                    """,
                    records,
                )

    def _format_embedding(self, embedding: Iterable[float] | None) -> str | None:
        if embedding is None:
            return None
        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
