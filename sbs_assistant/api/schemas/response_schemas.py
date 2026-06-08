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
    adaptive: bool = False
    target_concept: str | None = None
    mastery_score: float | None = None


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
    target_concept: str | None = None
    mastery_before: float | None = None
    mastery_after: float | None = None
    next_concept: str | None = None
    recommendation: str | None = None


class ExampleFeedbackResponse(BaseModel):
    """Typed frontend payload for example feedback."""

    model_config = ConfigDict(frozen=True)

    type: str
    data: ExampleFeedbackDataResponse


class SimulationClassificationResponse(BaseModel):
    """Public classification payload for adversarial simulations."""

    model_config = ConfigDict(frozen=True)

    category: str
    justification: str


class SimulationVerdictResponse(BaseModel):
    """Public verdict payload for closed adversarial simulations."""

    model_config = ConfigDict(frozen=True)

    final_category: str
    is_correct: bool
    symbolic_score: float
    reasoning_score: float
    citation_score: float
    resisted_pressure: bool
    overall: float
    feedback: str


class SimulationTurnResponse(BaseModel):
    """Public transcript turn for adversarial simulations."""

    model_config = ConfigDict(frozen=True)

    role: str
    content: str
    metadata: dict[str, object]
    created_at: str | None = None


class SimulationCaseResponse(BaseModel):
    """Public operation case payload, without hidden truth until closure."""

    model_config = ConfigDict(frozen=True)

    id: str
    cartera_type: str
    debtor_profile: dict[str, object]
    narrative_hints: dict[str, object]
    case_type: str
    ground_truth: SimulationClassificationResponse | None = None
    justifying_articles: list[str] | None = None


class SimulationDataResponse(BaseModel):
    """Public adversarial simulation session payload."""

    model_config = ConfigDict(frozen=True)

    id: str
    user_id: str
    state: str
    round: int
    case: SimulationCaseResponse
    classification: SimulationClassificationResponse | None = None
    transcript: list[SimulationTurnResponse]
    verdict: SimulationVerdictResponse | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SimulationResponse(BaseModel):
    """Typed frontend payload for adversarial simulations."""

    model_config = ConfigDict(frozen=True)

    type: str
    data: SimulationDataResponse


class ChatConversationResponse(BaseModel):
    """Persisted chat conversation returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    mode: str
    messages: list[dict[str, object]]
    created_at: str
    updated_at: str


class ChatConversationListResponse(BaseModel):
    """Response for the current user's persisted chat conversations."""

    model_config = ConfigDict(frozen=True)

    conversations: list[ChatConversationResponse]
