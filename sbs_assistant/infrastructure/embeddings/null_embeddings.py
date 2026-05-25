class NullEmbeddings:
    """Embedding adapter used when Vertex AI ingestion is disabled."""

    async def embed(self, text: str) -> list[float] | None:
        return None

    async def embed_query(self, text: str) -> list[float] | None:
        return None
