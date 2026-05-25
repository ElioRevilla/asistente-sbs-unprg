import httpx


class HttpPdfStorage:
    """Download PDFs over HTTP and optionally skip object storage."""

    def __init__(self, timeout_seconds: float = 60.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def download(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                raise ValueError(f"URL did not return a PDF: {content_type}")
            if not response.content.startswith(b"%PDF"):
                raise ValueError(
                    "URL response is not a valid PDF. Download the file manually "
                    "and rerun ingestion with --pdf-path."
                )
            return response.content

    async def upload(self, file_name: str, content: bytes) -> str | None:
        return None
