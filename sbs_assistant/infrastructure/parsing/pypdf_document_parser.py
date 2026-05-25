from io import BytesIO

from pypdf import PdfReader

from sbs_assistant.domain.entities.parsed_document import ParsedDocument
from sbs_assistant.infrastructure.parsing.sbs_text_chunker import (
    SbsRegulationTextChunker,
)


class PypdfDocumentParser:
    """Parse the SBS PDF using local text extraction."""

    def __init__(self, chunker: SbsRegulationTextChunker | None = None) -> None:
        self._chunker = chunker or SbsRegulationTextChunker()

    async def parse(self, file_bytes: bytes, source_name: str) -> ParsedDocument:
        reader = PdfReader(BytesIO(file_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text)
        return ParsedDocument(
            chunks=self._chunker.chunk(text),
            provision_rules=self._chunker.extract_provision_rules(text),
        )
