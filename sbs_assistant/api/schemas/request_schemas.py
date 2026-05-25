from pydantic import BaseModel, ConfigDict, Field


class ExplainRequest(BaseModel):
    """Request for the Explícame pedagogical mode."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1, max_length=1200)
    student_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class GenerateExampleRequestSchema(BaseModel):
    """Request for generating an Ejemplifica exercise."""

    model_config = ConfigDict(frozen=True)

    concept: str = Field(min_length=1, max_length=200)
    student_id: str | None = None
    use_llm_variation: bool = False


class ValidateExampleAnswerRequestSchema(BaseModel):
    """Request for validating an Ejemplifica answer."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    selected_category: str = Field(min_length=1, max_length=80)
    student_id: str | None = None
