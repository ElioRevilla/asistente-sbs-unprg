from sbs_assistant.infrastructure.retrieval.postgres_hybrid_retriever import (
    PostgresHybridRetriever,
)


def test_format_embedding_uses_pgvector_literal() -> None:
    retriever = PostgresHybridRetriever(pool=object(), embeddings=object())  # type: ignore[arg-type]

    assert retriever._format_embedding([0.123456789, 1.0]) == "[0.12345679,1.00000000]"


def test_build_filter_clause_supports_expected_filters() -> None:
    retriever = PostgresHybridRetriever(pool=object(), embeddings=object())  # type: ignore[arg-type]

    clause = retriever._build_filter_clause(
        {
            "temas": ["provisiones", "garantias"],
            "tipo_contenido": "tabla",
            "articulo": 2,
        },
        start_index=4,
    )

    assert "temas && $4::text[]" in clause.sql
    assert "tipo_contenido = $5" in clause.sql
    assert "articulo = $6" in clause.sql
    assert clause.params == [["provisiones", "garantias"], "tabla", 2]


def test_build_fts_query_removes_question_noise() -> None:
    retriever = PostgresHybridRetriever(pool=object(), embeddings=object())  # type: ignore[arg-type]

    query = (
        "¿A partir de cuántos días de atraso un deudor pasa a categoría " "Deficiente?"
    )

    assert retriever._build_fts_query(query) == (
        "días atraso deudor categoría deficiente"
    )


def test_build_fts_query_normalizes_category_without_accent() -> None:
    retriever = PostgresHybridRetriever(pool=object(), embeddings=object())  # type: ignore[arg-type]

    assert retriever._build_fts_query("categoria deficiente dias") == (
        "categoría deficiente dias"
    )


def test_build_filter_clause_is_empty_without_filters() -> None:
    retriever = PostgresHybridRetriever(pool=object(), embeddings=object())  # type: ignore[arg-type]

    clause = retriever._build_filter_clause(None, start_index=1)

    assert clause.sql == ""
    assert clause.params == []
