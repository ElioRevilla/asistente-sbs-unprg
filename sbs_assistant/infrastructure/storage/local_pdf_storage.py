from pathlib import Path


class LocalPdfStorage:
    """Read a local PDF file and optionally skip object storage."""

    def __init__(self, pdf_path: Path) -> None:
        self._pdf_path = pdf_path

    async def download(self, url: str) -> bytes:
        content = self._pdf_path.read_bytes()
        if not content.startswith(b"%PDF"):
            raise ValueError(f"Local file is not a valid PDF: {self._pdf_path}")
        return content

    async def upload(self, file_name: str, content: bytes) -> str | None:
        return None
