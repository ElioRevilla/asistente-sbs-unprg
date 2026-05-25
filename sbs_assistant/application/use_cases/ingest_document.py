from dataclasses import dataclass, replace

from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.ports.chunk_repository_port import ChunkRepositoryPort
from sbs_assistant.domain.ports.document_parser_port import DocumentParserPort
from sbs_assistant.domain.ports.embeddings_port import EmbeddingsPort
from sbs_assistant.domain.ports.pdf_storage_port import PdfStoragePort
from sbs_assistant.domain.ports.provision_rule_repository_port import (
    ProvisionRuleRepositoryPort,
)


@dataclass(frozen=True, slots=True)
class IngestDocumentRequest:
    """Input for ingesting the SBS regulation."""

    source_url: str
    file_name: str = "sbs_res_11356_2008.pdf"


@dataclass(frozen=True, slots=True)
class IngestDocumentResult:
    """Summary returned after a successful ingestion."""

    chunks_count: int
    provision_rules_count: int
    source_url: str
    storage_uri: str | None


class IngestDocumentUseCase:
    """Ingest the SBS PDF into the regulatory chunk store."""

    def __init__(
        self,
        pdf_storage: PdfStoragePort,
        parser: DocumentParserPort,
        embeddings: EmbeddingsPort,
        chunk_repository: ChunkRepositoryPort,
        provision_rule_repository: ProvisionRuleRepositoryPort,
    ) -> None:
        self._pdf_storage = pdf_storage
        self._parser = parser
        self._embeddings = embeddings
        self._chunk_repository = chunk_repository
        self._provision_rule_repository = provision_rule_repository

    async def execute(self, request: IngestDocumentRequest) -> IngestDocumentResult:
        pdf_bytes = await self._pdf_storage.download(request.source_url)
        storage_uri = await self._pdf_storage.upload(request.file_name, pdf_bytes)
        parsed_document = await self._parser.parse(pdf_bytes, request.file_name)

        embedded_chunks = await self._embed_chunks(parsed_document.chunks)

        await self._chunk_repository.save_many(embedded_chunks)
        await self._provision_rule_repository.replace_all(
            parsed_document.provision_rules
        )

        return IngestDocumentResult(
            chunks_count=len(embedded_chunks),
            provision_rules_count=len(parsed_document.provision_rules),
            source_url=request.source_url,
            storage_uri=storage_uri,
        )

    async def _embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        embedded_chunks: list[Chunk] = []
        for chunk in chunks:
            embedding = await self._embeddings.embed(chunk.text)
            embedded_chunks.append(replace(chunk, embedding=embedding))
        return embedded_chunks
