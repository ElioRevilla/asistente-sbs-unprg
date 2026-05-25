from typing import Protocol


class EmbeddingsPort(Protocol):
    """Port for generating text embeddings."""

    async def embed(self, text: str) -> list[float] | None:
        """Return an embedding vector for text, or None when disabled."""
