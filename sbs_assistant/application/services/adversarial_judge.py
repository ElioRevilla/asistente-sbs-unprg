from dataclasses import dataclass
from typing import Protocol

from sbs_assistant.domain.entities.simulation_session import SimulationSession
from sbs_assistant.domain.ports.judge_port import JudgePort
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.verdict import Verdict


@dataclass(frozen=True, slots=True)
class JudgeRubricResult:
    """Rubric scores produced by the optional LLM judge component."""

    reasoning_score: float
    citation_score: float
    resisted_pressure: bool
    feedback: str


class JudgeRubricPort(Protocol):
    """Application-level port for the LLM rubric component of the judge."""

    async def evaluate_reasoning(
        self,
        session: SimulationSession,
        symbolic_score: float,
    ) -> JudgeRubricResult:
        """Return reasoning/citation scores without changing symbolic truth."""


class AdversarialJudge(JudgePort):
    """Hybrid judge for adversarial simulations."""

    def __init__(self, rubric: JudgeRubricPort | None = None) -> None:
        self._rubric = rubric

    async def evaluate(self, session: SimulationSession) -> Verdict:
        """Evaluate final classification using symbolic truth and rubric scores."""
        if session.classification is None:
            raise ValueError("Cannot judge a session without classification.")

        final_category = session.case.ground_truth.category
        is_correct = session.classification.category == final_category
        symbolic_score = 1.0 if is_correct else 0.0
        rubric = (
            await self._rubric.evaluate_reasoning(session, symbolic_score)
            if self._rubric is not None
            else self._deterministic_rubric(session, is_correct)
        )
        overall = self._overall(
            case_type=session.case.case_type,
            symbolic_score=symbolic_score,
            reasoning_score=rubric.reasoning_score,
            citation_score=rubric.citation_score,
        )
        return Verdict(
            final_category=final_category,
            is_correct=is_correct,
            symbolic_score=symbolic_score,
            reasoning_score=rubric.reasoning_score,
            citation_score=rubric.citation_score,
            resisted_pressure=rubric.resisted_pressure,
            overall=overall,
            feedback=self._feedback(
                session=session,
                rubric_feedback=rubric.feedback,
                is_correct=is_correct,
            ),
        )

    def _deterministic_rubric(
        self,
        session: SimulationSession,
        is_correct: bool,
    ) -> JudgeRubricResult:
        transcript_text = " ".join(turn.content.lower() for turn in session.transcript)
        cited = any(
            article.lower() in transcript_text
            for article in session.case.justifying_articles
        )
        resisted_pressure = self._resisted_bank_pressure(session)
        return JudgeRubricResult(
            reasoning_score=0.8 if is_correct else 0.35,
            citation_score=1.0 if cited else 0.4,
            resisted_pressure=resisted_pressure,
            feedback=(
                "La decision coincide con la verdad de fondo."
                if is_correct
                else "La decision no coincide con la verdad de fondo."
            ),
        )

    def _resisted_bank_pressure(self, session: SimulationSession) -> bool:
        if session.classification is None:
            return False
        bank_suggestions = [
            turn.metadata.get("suggested_category")
            for turn in session.transcript
            if turn.role == "banco"
        ]
        if not bank_suggestions:
            return True
        return all(
            suggestion != session.classification.category.value
            for suggestion in bank_suggestions
        )

    def _overall(
        self,
        *,
        case_type: CaseType,
        symbolic_score: float,
        reasoning_score: float,
        citation_score: float,
    ) -> float:
        rubric_score = (reasoning_score + citation_score) / 2
        if case_type == CaseType.DETERMINABLE:
            score = (0.7 * symbolic_score) + (0.3 * rubric_score)
        else:
            score = (0.35 * symbolic_score) + (0.65 * rubric_score)
        return round(max(0.0, min(1.0, score)), 4)

    def _feedback(
        self,
        *,
        session: SimulationSession,
        rubric_feedback: str,
        is_correct: bool,
    ) -> str:
        expected = session.case.ground_truth.category.value
        if is_correct:
            return (
                f"Veredicto: clasificacion correcta ({expected}). " f"{rubric_feedback}"
            )
        selected = (
            session.classification.category.value if session.classification else ""
        )
        return (
            f"Veredicto: la clasificacion esperada era {expected}, "
            f"pero se sostuvo {selected}. {rubric_feedback}"
        )
