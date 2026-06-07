from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.application.services.adaptive_example_policy import (
    AdaptiveExamplePolicy,
)
from sbs_assistant.domain.ports.example_mastery_repository_port import (
    ExampleMasteryRepositoryPort,
)
from sbs_assistant.domain.ports.synthetic_case_repository_port import (
    SyntheticCaseRepositoryPort,
)
from sbs_assistant.domain.value_objects.category import Category


@dataclass(frozen=True, slots=True)
class ValidateExampleAnswerRequest:
    """Student answer for a generated example case."""

    case_id: UUID
    selected_category: str
    student_id: str | None = None


@dataclass(frozen=True, slots=True)
class ValidateExampleAnswerResult:
    """Feedback for a student's classification answer."""

    correct: bool
    correct_category: str
    feedback: str
    source_article: str
    target_concept: str | None = None
    mastery_before: float | None = None
    mastery_after: float | None = None
    next_concept: str | None = None
    recommendation: str | None = None


class ValidateExampleAnswerUseCase:
    """Validate an Ejemplifica answer using stored deterministic truth."""

    def __init__(
        self,
        repository: SyntheticCaseRepositoryPort,
        mastery_repository: ExampleMasteryRepositoryPort | None = None,
        adaptive_policy: AdaptiveExamplePolicy | None = None,
    ) -> None:
        self._repository = repository
        self._mastery_repository = mastery_repository
        self._adaptive_policy = adaptive_policy or AdaptiveExamplePolicy()

    async def execute(
        self,
        request: ValidateExampleAnswerRequest,
    ) -> ValidateExampleAnswerResult:
        synthetic_case = await self._repository.get(request.case_id)
        if synthetic_case is None:
            raise ValueError("No se encontró el caso indicado.")
        if synthetic_case.correct_category is None:
            raise ValueError("El caso no tiene categoría correcta registrada.")

        selected = self._normalize_category(request.selected_category)
        correct_category = synthetic_case.correct_category
        correct = selected == correct_category
        adaptive_update = None
        if request.student_id and self._mastery_repository is not None:
            target_concept = self._adaptive_policy.concept_for_case(synthetic_case)
            current_mastery = await self._mastery_repository.get(
                student_key=request.student_id,
                concept=target_concept,
            )
            next_mastery, adaptive_update = self._adaptive_policy.update(
                student_key=request.student_id,
                synthetic_case=synthetic_case,
                selected_category=selected,
                current_mastery=current_mastery,
                correct=correct,
            )
            await self._mastery_repository.upsert(next_mastery)

        return ValidateExampleAnswerResult(
            correct=correct,
            correct_category=correct_category.value,
            feedback=self._build_feedback(
                correct=correct,
                correct_category=correct_category,
                source_article=synthetic_case.source_article or "Reglamento SBS",
            ),
            source_article=synthetic_case.source_article or "Reglamento SBS",
            target_concept=(
                adaptive_update.target_concept if adaptive_update is not None else None
            ),
            mastery_before=(
                adaptive_update.mastery_before if adaptive_update is not None else None
            ),
            mastery_after=(
                adaptive_update.mastery_after if adaptive_update is not None else None
            ),
            next_concept=(
                adaptive_update.next_concept if adaptive_update is not None else None
            ),
            recommendation=(
                adaptive_update.recommendation if adaptive_update is not None else None
            ),
        )

    def _build_feedback(
        self,
        correct: bool,
        correct_category: Category,
        source_article: str,
    ) -> str:
        if correct:
            return (
                f"Correcto. El caso corresponde a la categoría "
                f"{correct_category.value} ({source_article})."
            )
        return (
            f"No exactamente. La categoría correcta es {correct_category.value}. "
            f"Revisa el criterio de días de atraso indicado en {source_article}."
        )

    def _normalize_category(self, value: str) -> Category | None:
        normalized = value.strip().lower()
        for category in Category:
            if normalized == category.value.lower():
                return category
        if normalized == "perdida":
            return Category.PERDIDA
        return None
