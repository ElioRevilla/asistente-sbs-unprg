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
    adaptive: bool = False


class ValidateExampleAnswerRequestSchema(BaseModel):
    """Request for validating an Ejemplifica answer."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    selected_category: str = Field(min_length=1, max_length=80)
    student_id: str | None = None


class StartSimulationRequestSchema(BaseModel):
    """Request for starting an adversarial simulation."""

    model_config = ConfigDict(frozen=True)

    focus: str | None = Field(default=None, max_length=200)
    student_id: str | None = None


class SubmitSimulationClassificationRequestSchema(BaseModel):
    """Request for submitting the student's initial simulation classification."""

    model_config = ConfigDict(frozen=True)

    category: str = Field(min_length=1, max_length=80)
    justification: str = Field(min_length=1, max_length=1200)


class AdvanceSimulationTurnRequestSchema(BaseModel):
    """Request for advancing an adversarial simulation with a defense."""

    model_config = ConfigDict(frozen=True)

    defense: str = Field(min_length=1, max_length=1600)


class ChatConversationUpsertRequest(BaseModel):
    """Request for creating or updating a persisted chat conversation."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=160)
    mode: str = Field(pattern="^(explicame|ejemplifica)$")
    messages: list[dict[str, object]] = Field(default_factory=list, max_length=200)
