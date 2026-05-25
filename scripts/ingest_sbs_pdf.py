"""Ingest the real SBS regulation PDF into PostgreSQL."""

# ruff: noqa: E402

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sbs_assistant.application.use_cases.ingest_document import (
    IngestDocumentRequest,
    IngestDocumentUseCase,
)
from sbs_assistant.config.settings import Settings
from sbs_assistant.infrastructure.embeddings.null_embeddings import NullEmbeddings
from sbs_assistant.infrastructure.embeddings.vertex_embeddings import VertexEmbeddings
from sbs_assistant.infrastructure.parsing.pypdf_document_parser import (
    PypdfDocumentParser,
)
from sbs_assistant.infrastructure.persistence.connection import (
    close_cloud_sql_connectors,
    create_pool,
)
from sbs_assistant.infrastructure.persistence.postgres_chunk_repo import (
    PostgresChunkRepository,
)
from sbs_assistant.infrastructure.persistence.postgres_provision_rule_repo import (
    PostgresProvisionRuleRepository,
)
from sbs_assistant.infrastructure.storage.gcs_storage import GcsPdfStorage
from sbs_assistant.infrastructure.storage.http_pdf_storage import HttpPdfStorage
from sbs_assistant.infrastructure.storage.local_pdf_storage import LocalPdfStorage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-url", default=None)
    parser.add_argument(
        "--pdf-path",
        default=None,
        help="Use a local PDF file instead of downloading SBS_PDF_URL.",
    )
    parser.add_argument("--file-name", default="sbs_res_11356_2008.pdf")
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Generate Vertex AI embeddings before writing chunks.",
    )
    parser.add_argument(
        "--skip-gcs",
        action="store_true",
        help="Do not upload the source PDF to Cloud Storage.",
    )
    return parser.parse_args()


def build_embeddings(
    settings: Settings, enabled: bool
) -> NullEmbeddings | VertexEmbeddings:
    if not enabled:
        return NullEmbeddings()
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required when --with-embeddings is used")
    return VertexEmbeddings(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.embeddings_model,
    )


def build_pdf_storage(
    settings: Settings,
    skip_gcs: bool,
    pdf_path: str | None,
) -> HttpPdfStorage | GcsPdfStorage | LocalPdfStorage:
    if pdf_path:
        return LocalPdfStorage(Path(pdf_path))
    if skip_gcs or not settings.gcs_bucket_docs:
        return HttpPdfStorage()
    return GcsPdfStorage(bucket_name=settings.gcs_bucket_docs)


async def main() -> None:
    args = parse_args()
    settings = Settings()
    pool = await create_pool(settings)
    try:
        use_case = IngestDocumentUseCase(
            pdf_storage=build_pdf_storage(
                settings,
                skip_gcs=args.skip_gcs,
                pdf_path=args.pdf_path,
            ),
            parser=PypdfDocumentParser(),
            embeddings=build_embeddings(settings, enabled=args.with_embeddings),
            chunk_repository=PostgresChunkRepository(pool),
            provision_rule_repository=PostgresProvisionRuleRepository(pool),
        )
        result = await use_case.execute(
            IngestDocumentRequest(
                source_url=args.pdf_url or settings.sbs_pdf_url,
                file_name=args.file_name,
            )
        )
        print(
            "Ingestion completed: "
            f"{result.chunks_count} chunks, "
            f"{result.provision_rules_count} provision rules, "
            f"storage_uri={result.storage_uri}"
        )
    finally:
        await pool.close()
        await close_cloud_sql_connectors()


if __name__ == "__main__":
    asyncio.run(main())
