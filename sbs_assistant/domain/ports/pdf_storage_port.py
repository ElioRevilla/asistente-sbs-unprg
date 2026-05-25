from typing import Protocol


class PdfStoragePort(Protocol):
    """Port for retrieving and optionally storing PDF files."""

    async def download(self, url: str) -> bytes:
        """Download a PDF from a URL."""

    async def upload(self, file_name: str, content: bytes) -> str | None:
        """Upload a PDF and return its URI when storage is configured."""
