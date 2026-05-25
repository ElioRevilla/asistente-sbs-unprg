from decimal import Decimal

import pytest

from sbs_assistant.application.use_cases.ingest_document import (
    IngestDocumentRequest,
    IngestDocumentUseCase,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.parsed_document import ParsedDocument
from sbs_assistant.domain.entities.provision_rule import ProvisionRule
from sbs_assistant.domain.value_objects.category import Category
from sbs_assistant.domain.value_objects.credit_type import CreditType


class FakePdfStorage:
    def __init__(self) -> None:
        self.uploaded: tuple[str, bytes] | None = None

    async def download(self, url: str) -> bytes:
        return b"%PDF fake"

    async def upload(self, file_name: str, content: bytes) -> str | None:
        self.uploaded = (file_name, content)
        return f"gs://bucket/{file_name}"


class FakeParser:
    async def parse(self, file_bytes: bytes, source_name: str) -> ParsedDocument:
        return ParsedDocument(
            chunks=[
                Chunk(
                    id="art_1",
                    article=1,
                    text="Articulo 1. Clasificacion del deudor.",
                )
            ],
            provision_rules=[
                ProvisionRule(
                    category=Category.NORMAL,
                    credit_type=CreditType.CONSUMO,
                    guarantee_type=None,
                    provision_percentage=Decimal("1.00"),
                    source_article="Articulo 1",
                )
            ],
        )


class FakeEmbeddings:
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeChunkRepository:
    def __init__(self) -> None:
        self.saved: list[Chunk] = []

    async def save_many(self, chunks: list[Chunk]) -> None:
        self.saved = chunks


class FakeProvisionRuleRepository:
    def __init__(self) -> None:
        self.saved: list[ProvisionRule] = []

    async def replace_all(self, rules: list[ProvisionRule]) -> None:
        self.saved = rules


@pytest.mark.asyncio
async def test_ingest_document_downloads_parses_embeds_and_persists() -> None:
    pdf_storage = FakePdfStorage()
    chunk_repository = FakeChunkRepository()
    rule_repository = FakeProvisionRuleRepository()
    use_case = IngestDocumentUseCase(
        pdf_storage=pdf_storage,
        parser=FakeParser(),
        embeddings=FakeEmbeddings(),
        chunk_repository=chunk_repository,
        provision_rule_repository=rule_repository,
    )

    result = await use_case.execute(
        IngestDocumentRequest(
            source_url="https://example.test/reglamento.pdf",
            file_name="reglamento.pdf",
        )
    )

    assert result.chunks_count == 1
    assert result.provision_rules_count == 1
    assert result.storage_uri == "gs://bucket/reglamento.pdf"
    assert chunk_repository.saved[0].embedding == [0.1, 0.2, 0.3]
    assert rule_repository.saved[0].category == Category.NORMAL
