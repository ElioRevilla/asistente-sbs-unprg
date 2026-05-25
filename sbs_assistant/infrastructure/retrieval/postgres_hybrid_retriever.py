from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import asyncpg

from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.ports.embeddings_port import EmbeddingsPort

_FTS_STOPWORDS = {
    "a",
    "al",
    "ante",
    "como",
    "con",
    "cual",
    "cuando",
    "cuantos",
    "cuantas",
    "de",
    "del",
    "desde",
    "el",
    "en",
    "entre",
    "es",
    "esta",
    "este",
    "ha",
    "hasta",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "ntos",
    "para",
    "partir",
    "pasa",
    "por",
    "que",
    "se",
    "si",
    "sobre",
    "son",
    "su",
    "un",
    "una",
}

_FTS_ALIASES = {
    "categor": "categoría",
    "categoria": "categoría",
    "categoría": "categoría",
}


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned by hybrid retrieval with its fused relevance score."""

    chunk: Chunk
    score: float


class PostgresHybridRetriever:
    """Hybrid PostgreSQL retriever using pgvector, FTS and RRF fusion."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        embeddings: EmbeddingsPort,
        rrf_k: int = 60,
    ) -> None:
        self._pool = pool
        self._embeddings = embeddings
        self._rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        """Retrieve relevant chunks without scores."""
        results = await self.retrieve_with_scores(query, top_k=top_k, filters=filters)
        return [result.chunk for result in results]

    async def retrieve_with_scores(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks with RRF scores."""
        query_embedding = await self._embed_query(query)
        candidate_limit = max(top_k * 5, 20)

        async with self._pool.acquire() as connection:
            if query_embedding is None:
                rows = await self._fetch_text_results(
                    connection,
                    query=query,
                    top_k=top_k,
                    candidate_limit=candidate_limit,
                    filters=filters,
                )
            else:
                rows = await self._fetch_hybrid_results(
                    connection,
                    query=query,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    candidate_limit=candidate_limit,
                    filters=filters,
                )
        return [self._row_to_result(row) for row in rows]

    async def _embed_query(self, query: str) -> list[float] | None:
        embed_query = getattr(self._embeddings, "embed_query", None)
        if embed_query is not None:
            return await embed_query(query)
        return await self._embeddings.embed(query)

    async def _fetch_hybrid_results(
        self,
        connection: asyncpg.Connection,
        query: str,
        query_embedding: Sequence[float],
        top_k: int,
        candidate_limit: int,
        filters: dict[str, object] | None,
    ) -> list[asyncpg.Record]:
        fts_query = self._build_fts_query(query)
        vector_filter = self._build_filter_clause(filters, start_index=4)
        text_filter = self._build_filter_clause(
            filters,
            start_index=4 + len(vector_filter.params),
        )
        final_filter = self._build_filter_clause(
            filters,
            start_index=4 + len(vector_filter.params) + len(text_filter.params),
        )
        limit_param_index = (
            4
            + len(vector_filter.params)
            + len(text_filter.params)
            + len(final_filter.params)
        )
        sql = f"""
            WITH vector_results AS (
              SELECT
                id,
                row_number() OVER (ORDER BY embedding <=> $1::vector) AS rank
              FROM chunks
              WHERE embedding IS NOT NULL
              {vector_filter.sql}
              ORDER BY embedding <=> $1::vector
              LIMIT $2
            ),
            text_results AS (
              SELECT
                id,
                row_number() OVER (
                  ORDER BY ts_rank_cd(to_tsvector('spanish', texto), query.tsq) DESC
                ) AS rank
              FROM chunks, plainto_tsquery('spanish', $3) AS query(tsq)
              WHERE query.tsq @@ to_tsvector('spanish', texto)
              {text_filter.sql}
              ORDER BY ts_rank_cd(to_tsvector('spanish', texto), query.tsq) DESC
              LIMIT $2
            ),
            fused AS (
              SELECT id, SUM(score) AS score
              FROM (
                SELECT id, 1.0 / ({self._rrf_k} + rank) AS score
                FROM vector_results
                UNION ALL
                SELECT id, 1.0 / ({self._rrf_k} + rank) AS score
                FROM text_results
              ) ranked
              GROUP BY id
            )
            SELECT
              chunks.id,
              chunks.capitulo,
              chunks.articulo,
              chunks.numeral,
              chunks.tipo_contenido,
              chunks.temas,
              chunks.texto,
              chunks.referencias_cruzadas,
              chunks.created_at,
              fused.score
            FROM fused
            JOIN chunks ON chunks.id = fused.id
            WHERE TRUE
            {final_filter.sql}
            ORDER BY fused.score DESC, chunks.id
            LIMIT ${limit_param_index}
        """
        params: list[Any] = [
            self._format_embedding(query_embedding),
            candidate_limit,
            fts_query,
            *vector_filter.params,
            *text_filter.params,
            *final_filter.params,
            top_k,
        ]
        return list(await connection.fetch(sql, *params))

    async def _fetch_text_results(
        self,
        connection: asyncpg.Connection,
        query: str,
        top_k: int,
        candidate_limit: int,
        filters: dict[str, object] | None,
    ) -> list[asyncpg.Record]:
        fts_query = self._build_fts_query(query)
        filter_clause = self._build_filter_clause(filters, start_index=3)
        sql = f"""
            WITH text_results AS (
              SELECT
                id,
                row_number() OVER (
                  ORDER BY ts_rank_cd(to_tsvector('spanish', texto), query.tsq) DESC
                ) AS rank
              FROM chunks, plainto_tsquery('spanish', $1) AS query(tsq)
              WHERE query.tsq @@ to_tsvector('spanish', texto)
              {filter_clause.sql}
              ORDER BY ts_rank_cd(to_tsvector('spanish', texto), query.tsq) DESC
              LIMIT $2
            )
            SELECT
              chunks.id,
              chunks.capitulo,
              chunks.articulo,
              chunks.numeral,
              chunks.tipo_contenido,
              chunks.temas,
              chunks.texto,
              chunks.referencias_cruzadas,
              chunks.created_at,
              1.0 / ({self._rrf_k} + text_results.rank) AS score
            FROM text_results
            JOIN chunks ON chunks.id = text_results.id
            ORDER BY score DESC, chunks.id
            LIMIT ${3 + len(filter_clause.params)}
        """
        params: list[Any] = [fts_query, candidate_limit, *filter_clause.params, top_k]
        return list(await connection.fetch(sql, *params))

    def _row_to_result(self, row: asyncpg.Record) -> RetrievedChunk:
        return RetrievedChunk(
            chunk=Chunk(
                id=row["id"],
                chapter=row["capitulo"],
                article=row["articulo"],
                numeral=row["numeral"],
                content_type=row["tipo_contenido"],
                topics=list(row["temas"] or []),
                text=row["texto"],
                cross_references=list(row["referencias_cruzadas"] or []),
                created_at=self._coerce_datetime(row["created_at"]),
            ),
            score=float(row["score"]),
        )

    def _format_embedding(self, embedding: Iterable[float]) -> str:
        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"

    def _coerce_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        return None

    def _build_fts_query(self, query: str) -> str:
        """Reduce natural questions to useful terms for PostgreSQL FTS."""
        tokens = re.findall(r"[^\W_]+", query.lower(), flags=re.UNICODE)
        selected_tokens: list[str] = []
        for token in tokens:
            stopword_key = self._strip_accents(token)
            if len(token) <= 2 or stopword_key in _FTS_STOPWORDS:
                continue
            selected_token = _FTS_ALIASES.get(stopword_key, token)
            if selected_token not in selected_tokens:
                selected_tokens.append(selected_token)
        return " ".join(selected_tokens) or query

    def _strip_accents(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    def _build_filter_clause(
        self,
        filters: dict[str, object] | None,
        start_index: int,
    ) -> _FilterClause:
        if not filters:
            return _FilterClause(sql="", params=[])

        clauses: list[str] = []
        params: list[object] = []

        if topics := filters.get("temas"):
            params.append(list(topics) if isinstance(topics, list) else [str(topics)])
            clauses.append(f"AND temas && ${start_index + len(params) - 1}::text[]")

        if content_type := filters.get("tipo_contenido"):
            params.append(str(content_type))
            clauses.append(f"AND tipo_contenido = ${start_index + len(params) - 1}")

        if article := filters.get("articulo"):
            params.append(int(article))
            clauses.append(f"AND articulo = ${start_index + len(params) - 1}")

        return _FilterClause(
            sql="\n              " + "\n              ".join(clauses),
            params=params,
        )


@dataclass(frozen=True, slots=True)
class _FilterClause:
    sql: str
    params: list[object]
