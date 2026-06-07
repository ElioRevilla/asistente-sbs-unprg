from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.services.adaptive_example_policy import (
    AdaptiveExamplePolicy,
)
from sbs_assistant.application.services.example_case_templates import (
    TemplateExampleCaseGenerator,
)
from sbs_assistant.application.services.llm_example_variation import (
    LLMExampleCaseVariationService,
)
from sbs_assistant.domain.ports.example_mastery_repository_port import (
    ExampleMasteryRepositoryPort,
)
from sbs_assistant.domain.ports.synthetic_case_repository_port import (
    SyntheticCaseRepositoryPort,
)

CATEGORY_OPTIONS = ["Normal", "CPP", "Deficiente", "Dudoso", "Pérdida"]


@dataclass(frozen=True, slots=True)
class GenerateExampleRequest:
    """Input for the Ejemplifica generation use case."""

    concept: str
    student_id: str | None = None
    use_llm_variation: bool = False
    adaptive: bool = False


@dataclass(frozen=True, slots=True)
class GenerateExampleResult:
    """Generated classification exercise for the student."""

    case_id: UUID
    concept: str
    case_data: dict[str, object]
    options: list[str]
    source_article: str
    adaptive: bool = False
    target_concept: str | None = None
    mastery_score: float | None = None


class GenerateExampleUseCase:
    """Generate an auditable synthetic debtor case from templates."""

    def __init__(
        self,
        repository: SyntheticCaseRepositoryPort,
        mastery_repository: ExampleMasteryRepositoryPort | None = None,
        generator: TemplateExampleCaseGenerator | None = None,
        adaptive_policy: AdaptiveExamplePolicy | None = None,
        variation_service: LLMExampleCaseVariationService | None = None,
    ) -> None:
        self._repository = repository
        self._mastery_repository = mastery_repository
        self._generator = generator or TemplateExampleCaseGenerator()
        self._adaptive_policy = adaptive_policy or AdaptiveExamplePolicy()
        self._variation_service = variation_service

    async def execute(self, request: GenerateExampleRequest) -> GenerateExampleResult:
        concept = request.concept
        target_concept: str | None = None
        mastery_score: float | None = None
        variant_index = 0
        if (
            request.adaptive
            and request.student_id
            and self._mastery_repository is not None
        ):
            records = await self._mastery_repository.list_by_student(
                request.student_id,
            )
            target = self._adaptive_policy.target_from_mastery(
                records=records,
                requested_concept=request.concept,
            )
            concept = target.prompt
            target_concept = target.concept
            mastery_score = target.mastery_score
            variant_index = target.variant_index

        synthetic_case = self._generator.generate(
            concept,
            variant_index=variant_index,
        )
        if request.use_llm_variation and self._variation_service is not None:
            synthetic_case = await self._variation_service.vary(
                case=synthetic_case,
                concept=concept,
            )
        saved_case = await self._repository.save(synthetic_case)
        if saved_case.id is None:
            raise RuntimeError("Synthetic case repository did not return an ID")

        return GenerateExampleResult(
            case_id=saved_case.id,
            concept=concept,
            case_data=saved_case.description,
            options=CATEGORY_OPTIONS,
            source_article=saved_case.source_article or "Reglamento SBS",
            adaptive=request.adaptive,
            target_concept=target_concept,
            mastery_score=mastery_score,
        )
