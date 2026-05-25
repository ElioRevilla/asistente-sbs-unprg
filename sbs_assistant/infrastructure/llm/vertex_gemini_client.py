import asyncio

from vertexai import init
from vertexai.generative_models import GenerativeModel


class VertexGeminiClient:
    """Generate text with Gemini through Vertex AI."""

    def __init__(self, project_id: str, location: str, model_name: str) -> None:
        self._project_id = project_id
        self._location = location
        self._model_name = model_name
        init(project=project_id, location=location)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response from Gemini."""
        model = GenerativeModel(
            self._model_name,
            system_instruction=[system_prompt],
        )
        response = await asyncio.to_thread(model.generate_content, user_prompt)
        return response.text or ""
