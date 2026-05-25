from typing import Protocol

from sbs_assistant.domain.entities.chunk import Chunk


class ChunkRepositoryPort(Protocol):
    """Persistence port for regulatory chunks."""

    async def save_many(self, chunks: list[Chunk]) -> None:
        """Persist regulatory chunks."""
