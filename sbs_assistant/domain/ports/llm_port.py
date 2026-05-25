from typing import Protocol


class LLMPort(Protocol):
    """Port for LLM text generation."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a model response."""
