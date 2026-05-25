from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.services.example_case_templates import (
    TemplateExampleCaseGenerator,
)
from sbs_assistant.application.services.llm_example_variation import (
    LLMExampleCaseVariationService,
)
from sbs_assistant.domain.ports.synthetic_case_repository_port import (
    SyntheticCaseRepositoryPort,
)

CATEGORY_OPTIONS = ["Normal", "CPP", "Deficiente", "Dudoso", "Pérdida"]


@dataclass(frozen=True, slots=True)
class GenerateExampleRequest:
    """Input for the Ejemplifica generation use case."""

    concept: str
    use_llm_variation: bool = False


@dataclass(frozen=True, slots=True)
class GenerateExampleResult:
    """Generated classification exercise for the student."""

    case_id: UUID
    concept: str
    case_data: dict[str, object]
    options: list[str]
    source_article: str


class GenerateExampleUseCase:
    """Generate an auditable synthetic debtor case from templates."""

    def __init__(
        self,
        repository: SyntheticCaseRepositoryPort,
        generator: TemplateExampleCaseGenerator | None = None,
        variation_service: LLMExampleCaseVariationService | None = None,
    ) -> None:
        self._repository = repository
        self._generator = generator or TemplateExampleCaseGenerator()
        self._variation_service = variation_service

    async def execute(self, request: GenerateExampleRequest) -> GenerateExampleResult:
        synthetic_case = self._generator.generate(request.concept)
        if request.use_llm_variation and self._variation_service is not None:
            synthetic_case = await self._variation_service.vary(
                case=synthetic_case,
                concept=request.concept,
            )
        saved_case = await self._repository.save(synthetic_case)
        if saved_case.id is None:
            raise RuntimeError("Synthetic case repository did not return an ID")

        return GenerateExampleResult(
            case_id=saved_case.id,
            concept=request.concept,
            case_data=saved_case.description,
            options=CATEGORY_OPTIONS,
            source_article=saved_case.source_article or "Reglamento SBS",
        )
