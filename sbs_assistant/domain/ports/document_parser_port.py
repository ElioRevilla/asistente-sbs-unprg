from typing import Protocol

from sbs_assistant.domain.entities.parsed_document import ParsedDocument


class DocumentParserPort(Protocol):
    """Port for parsing regulatory documents."""

    async def parse(self, file_bytes: bytes, source_name: str) -> ParsedDocument:
        """Parse a document into chunks and structured rules."""
