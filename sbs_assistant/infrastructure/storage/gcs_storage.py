from google.cloud import storage

from sbs_assistant.infrastructure.storage.http_pdf_storage import HttpPdfStorage


class GcsPdfStorage(HttpPdfStorage):
    """Download a PDF and upload the original file to Cloud Storage."""

    def __init__(
        self,
        bucket_name: str,
        prefix: str = "documents",
        timeout_seconds: float = 60.0,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._bucket_name = bucket_name
        self._prefix = prefix.strip("/")
        self._client = storage.Client()

    async def upload(self, file_name: str, content: bytes) -> str | None:
        bucket = self._client.bucket(self._bucket_name)
        blob_name = f"{self._prefix}/{file_name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type="application/pdf")
        return f"gs://{self._bucket_name}/{blob_name}"
