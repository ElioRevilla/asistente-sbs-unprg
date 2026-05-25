from dataclasses import dataclass
from uuid import UUID

from sbs_assistant.domain.ports.synthetic_case_repository_port import (
    SyntheticCaseRepositoryPort,
)
from sbs_assistant.domain.value_objects.category import Category


@dataclass(frozen=True, slots=True)
class ValidateExampleAnswerRequest:
    """Student answer for a generated example case."""

    case_id: UUID
    selected_category: str


@dataclass(frozen=True, slots=True)
class ValidateExampleAnswerResult:
    """Feedback for a student's classification answer."""

    correct: bool
    correct_category: str
    feedback: str
    source_article: str


class ValidateExampleAnswerUseCase:
    """Validate an Ejemplifica answer using stored deterministic truth."""

    def __init__(self, repository: SyntheticCaseRepositoryPort) -> None:
        self._repository = repository

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
        return ValidateExampleAnswerResult(
            correct=correct,
            correct_category=correct_category.value,
            feedback=self._build_feedback(
                correct=correct,
                correct_category=correct_category,
                source_article=synthetic_case.source_article or "Reglamento SBS",
            ),
            source_article=synthetic_case.source_article or "Reglamento SBS",
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
