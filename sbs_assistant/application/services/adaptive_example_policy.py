from dataclasses import dataclass

from sbs_assistant.domain.entities.case import SyntheticCase
from sbs_assistant.domain.entities.example_mastery import ExampleMastery
from sbs_assistant.domain.value_objects.category import Category

DEFAULT_MASTERY = 0.5
MASTERY_K = 0.15


@dataclass(frozen=True, slots=True)
class AdaptiveExampleUpdate:
    """Result of updating adaptive practice state."""

    target_concept: str
    mastery_before: float
    mastery_after: float
    attempts: int
    next_concept: str
    recommendation: str


@dataclass(frozen=True, slots=True)
class AdaptiveExampleTarget:
    """Next target selected for adaptive case generation."""

    concept: str
    mastery_score: float
    prompt: str
    variant_index: int = 0


class AdaptiveExamplePolicy:
    """Small deterministic policy for adaptive Ejemplifica practice."""

    _CATEGORY_TO_CONCEPT = {
        Category.NORMAL: "categoria_normal_minorista",
        Category.CPP: "categoria_cpp_minorista",
        Category.DEFICIENTE: "categoria_deficiente_minorista",
        Category.DUDOSO: "categoria_dudoso_minorista",
        Category.PERDIDA: "categoria_perdida_minorista",
    }
    _CONCEPT_TO_PROMPT = {
        "categoria_normal_minorista": "consumo no revolvente en categoria Normal",
        "categoria_cpp_minorista": "consumo no revolvente en categoria CPP",
        "categoria_deficiente_minorista": ("microempresa en categoria Deficiente"),
        "categoria_dudoso_minorista": "consumo no revolvente en categoria Dudoso",
        "categoria_perdida_minorista": "consumo no revolvente en categoria Perdida",
    }
    _DIFFICULTY = {
        "categoria_normal_minorista": 0.25,
        "categoria_cpp_minorista": 0.4,
        "categoria_deficiente_minorista": 0.55,
        "categoria_dudoso_minorista": 0.65,
        "categoria_perdida_minorista": 0.75,
    }
    _CONFUSABLES = {
        "categoria_normal_minorista": "categoria_cpp_minorista",
        "categoria_cpp_minorista": "categoria_deficiente_minorista",
        "categoria_deficiente_minorista": "categoria_cpp_minorista",
        "categoria_dudoso_minorista": "categoria_deficiente_minorista",
        "categoria_perdida_minorista": "categoria_dudoso_minorista",
    }
    _NEXT_AFTER_SUCCESS = {
        "categoria_normal_minorista": "categoria_cpp_minorista",
        "categoria_cpp_minorista": "categoria_deficiente_minorista",
        "categoria_deficiente_minorista": "categoria_dudoso_minorista",
        "categoria_dudoso_minorista": "categoria_perdida_minorista",
        "categoria_perdida_minorista": "categoria_deficiente_minorista",
    }

    def concept_for_case(self, synthetic_case: SyntheticCase) -> str:
        """Infer the evaluated concept from the deterministic case truth."""
        if synthetic_case.correct_category is None:
            return "categoria_deficiente_minorista"
        return self._CATEGORY_TO_CONCEPT.get(
            synthetic_case.correct_category,
            "categoria_deficiente_minorista",
        )

    def target_from_mastery(
        self,
        records: list[ExampleMastery],
        requested_concept: str,
    ) -> AdaptiveExampleTarget:
        """Choose the next concept using the weakest tracked mastery."""
        if not records:
            concept = self._concept_from_text(requested_concept)
            return AdaptiveExampleTarget(
                concept=concept,
                mastery_score=DEFAULT_MASTERY,
                prompt=self.prompt_for_concept(concept),
            )

        weakest = min(records, key=lambda item: (item.mastery_score, item.updated_at))
        concept = weakest.concept
        return AdaptiveExampleTarget(
            concept=concept,
            mastery_score=weakest.mastery_score,
            prompt=self.prompt_for_concept(concept),
            variant_index=weakest.attempts,
        )

    def update(
        self,
        *,
        student_key: str,
        synthetic_case: SyntheticCase,
        selected_category: Category | None,
        current_mastery: ExampleMastery | None,
        correct: bool,
    ) -> tuple[ExampleMastery, AdaptiveExampleUpdate]:
        """Update mastery and return pedagogical guidance."""
        target_concept = self.concept_for_case(synthetic_case)
        before = (
            current_mastery.mastery_score
            if current_mastery is not None
            else DEFAULT_MASTERY
        )
        attempts = current_mastery.attempts + 1 if current_mastery else 1
        difficulty = self._DIFFICULTY.get(target_concept, 0.55)
        after = self._next_score(before=before, difficulty=difficulty, correct=correct)
        next_concept = self._next_concept(
            target_concept=target_concept,
            selected_category=selected_category,
            correct=correct,
        )
        recommendation = self._recommendation(
            correct=correct,
            target_concept=target_concept,
            next_concept=next_concept,
        )
        mastery = ExampleMastery(
            student_key=student_key,
            concept=target_concept,
            mastery_score=after,
            attempts=attempts,
            last_answer_correct=correct,
        )
        return mastery, AdaptiveExampleUpdate(
            target_concept=target_concept,
            mastery_before=before,
            mastery_after=after,
            attempts=attempts,
            next_concept=next_concept,
            recommendation=recommendation,
        )

    def prompt_for_concept(self, concept: str) -> str:
        """Return a generator prompt for a canonical concept."""
        return self._CONCEPT_TO_PROMPT.get(
            concept,
            "microempresa en categoria Deficiente",
        )

    def _next_score(self, *, before: float, difficulty: float, correct: bool) -> float:
        if correct:
            score = before + MASTERY_K * (1 - before) * difficulty
        else:
            score = before - MASTERY_K * before * (1 - difficulty)
        return min(1.0, max(0.0, round(score, 4)))

    def _next_concept(
        self,
        *,
        target_concept: str,
        selected_category: Category | None,
        correct: bool,
    ) -> str:
        if correct:
            return self._NEXT_AFTER_SUCCESS.get(target_concept, target_concept)
        if selected_category is not None:
            selected_concept = self._CATEGORY_TO_CONCEPT.get(selected_category)
            if (
                selected_concept
                and selected_concept != target_concept
                and self._is_adjacent(target_concept, selected_concept)
            ):
                return selected_concept
        return self._CONFUSABLES.get(target_concept, target_concept)

    def _recommendation(
        self,
        *,
        correct: bool,
        target_concept: str,
        next_concept: str,
    ) -> str:
        if correct:
            return (
                "Buen avance. El siguiente caso sube un poco la dificultad "
                f"hacia {self._label(next_concept)}."
            )
        return (
            f"Conviene practicar {self._label(target_concept)} y compararlo "
            f"con {self._label(next_concept)}."
        )

    def _concept_from_text(self, concept: str) -> str:
        normalized = concept.lower()
        if "normal" in normalized:
            return "categoria_normal_minorista"
        if "cpp" in normalized or "problemas potenciales" in normalized:
            return "categoria_cpp_minorista"
        if "dudoso" in normalized:
            return "categoria_dudoso_minorista"
        if "perdida" in normalized or "pérdida" in normalized:
            return "categoria_perdida_minorista"
        return "categoria_deficiente_minorista"

    def _label(self, concept: str) -> str:
        return concept.replace("_", " ")

    def _is_adjacent(self, target_concept: str, selected_concept: str) -> bool:
        order = [
            "categoria_normal_minorista",
            "categoria_cpp_minorista",
            "categoria_deficiente_minorista",
            "categoria_dudoso_minorista",
            "categoria_perdida_minorista",
        ]
        try:
            return abs(order.index(target_concept) - order.index(selected_concept)) == 1
        except ValueError:
            return False
