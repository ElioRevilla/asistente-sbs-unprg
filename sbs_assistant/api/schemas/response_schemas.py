from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Response returned by the health endpoint."""

    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str


class CitationResponse(BaseModel):
    """Source citation returned by grounded pedagogical responses."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    label: str
    text_preview: str


class ExplainDataResponse(BaseModel):
    """Data payload for the Explícame mode."""

    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[CitationResponse]


class ExplainResponse(BaseModel):
    """Typed frontend payload for a text explanation."""

    model_config = ConfigDict(frozen=True)

    type: str
    data: ExplainDataResponse


class ExampleDataResponse(BaseModel):
    """Data payload for an Ejemplifica generated case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    concept: str
    case: dict[str, object]
    options: list[str]
    source_article: str


class ExampleResponse(BaseModel):
    """Typed frontend payload for an example exercise."""

    model_config = ConfigDict(frozen=True)

    type: str
    data: ExampleDataResponse


class ExampleFeedbackDataResponse(BaseModel):
    """Data payload for Ejemplifica answer feedback."""

    model_config = ConfigDict(frozen=True)

    correct: bool
    correct_category: str
    feedback: str
    source_article: str


class ExampleFeedbackResponse(BaseModel):
    """Typed frontend payload for example feedback."""

    model_config = ConfigDict(frozen=True)

    type: str
    data: ExampleFeedbackDataResponse
