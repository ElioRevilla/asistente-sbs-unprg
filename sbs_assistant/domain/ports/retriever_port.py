from typing import Protocol

from sbs_assistant.domain.entities.chunk import Chunk


class RetrieverPort(Protocol):
    """Port for hybrid retrieval over regulatory chunks."""

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        """Retrieve relevant chunks for a query."""
