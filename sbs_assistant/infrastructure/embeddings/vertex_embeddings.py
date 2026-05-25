from vertexai import init
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel


class VertexEmbeddings:
    """Generate embeddings with Vertex AI text-embedding models."""

    def __init__(self, project_id: str, location: str, model_name: str) -> None:
        init(project=project_id, location=location)
        self._model = TextEmbeddingModel.from_pretrained(model_name)

    async def embed(self, text: str) -> list[float] | None:
        return await self.embed_document(text)

    async def embed_document(self, text: str) -> list[float]:
        """Return an embedding optimized for indexed document chunks."""
        embedding_input = TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")
        embedding = self._model.get_embeddings([embedding_input])[0]
        return list(embedding.values)

    async def embed_query(self, text: str) -> list[float]:
        """Return an embedding optimized for retrieval queries."""
        embedding_input = TextEmbeddingInput(text, "RETRIEVAL_QUERY")
        embedding = self._model.get_embeddings([embedding_input])[0]
        return list(embedding.values)
