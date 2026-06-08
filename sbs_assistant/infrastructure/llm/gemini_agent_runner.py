import json
from dataclasses import asdict, is_dataclass
from typing import Any

from sbs_assistant.application.prompts.simulation import (
    BANCO_SYSTEM_PROMPT,
    CLIENTE_SYSTEM_PROMPT,
    JUDGE_RUBRIC_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)
from sbs_assistant.application.services.adversarial_judge import (
    JudgeRubricPort,
    JudgeRubricResult,
)
from sbs_assistant.domain.entities.agent_turn import (
    BancoTurnDTO,
    ClienteTurnDTO,
    SupervisorTurnDTO,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import SimulationSession
from sbs_assistant.domain.ports.debate_agent_port import DebateAgentPort
from sbs_assistant.domain.ports.llm_port import LLMPort
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory


class GeminiAgentRunner(DebateAgentPort, JudgeRubricPort):
    """Bounded Gemini runner for simulation agents and judge rubric."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def present(self, case: OperationCase) -> ClienteTurnDTO:
        """Return a client narrative without exposing hidden truth."""
        payload = {
            "debtor_profile": case.debtor_profile,
            "narrative_hints": case.narrative_hints,
        }
        data = await self._generate_json(CLIENTE_SYSTEM_PROMPT, payload)
        return ClienteTurnDTO(
            narrative=str(data.get("narrative") or self._fallback_client(case))
        )

    async def challenge(
        self,
        case: OperationCase,
        ground_truth: Classification,
        grounding_chunks: list[Chunk],
        last_defense: str | None,
        prior_objections: list[str],
    ) -> SupervisorTurnDTO:
        """Return a grounded supervisor challenge."""
        payload = {
            "debtor_profile": case.debtor_profile,
            "case_type": case.case_type.value,
            "ground_truth": _classification_payload(ground_truth),
            "justifying_articles": case.justifying_articles,
            "grounding_chunks": [_chunk_payload(chunk) for chunk in grounding_chunks],
            "last_defense": last_defense,
            "prior_objections": prior_objections,
        }
        data = await self._generate_json(SUPERVISOR_SYSTEM_PROMPT, payload)
        cited_articles = data.get("cited_articles")
        return SupervisorTurnDTO(
            challenge=str(data.get("challenge") or self._fallback_supervisor(case)),
            objection_remaining=bool(data.get("objection_remaining", True)),
            cited_articles=(
                [str(article) for article in cited_articles]
                if isinstance(cited_articles, list)
                else list(case.justifying_articles)
            ),
        )

    async def pressure(
        self,
        case: OperationCase,
        current_classification: Classification,
    ) -> BancoTurnDTO:
        """Return bank pressure without receiving hidden truth."""
        payload = {
            "debtor_profile": case.debtor_profile,
            "narrative_hints": case.narrative_hints,
            "current_classification": _classification_payload(current_classification),
        }
        data = await self._generate_json(BANCO_SYSTEM_PROMPT, payload)
        suggested = _risk_category_from_text(
            str(data.get("suggested_category") or RiskCategory.CPP.value)
        )
        return BancoTurnDTO(
            pressure=str(data.get("pressure") or self._fallback_bank()),
            suggested_category=suggested,
        )

    async def evaluate_reasoning(
        self,
        session: SimulationSession,
        symbolic_score: float,
    ) -> JudgeRubricResult:
        """Return rubric scores for the hybrid judge."""
        payload = {
            "case": {
                "debtor_profile": session.case.debtor_profile,
                "case_type": session.case.case_type.value,
                "ground_truth": _classification_payload(session.case.ground_truth),
                "justifying_articles": session.case.justifying_articles,
            },
            "student_classification": (
                _classification_payload(session.classification)
                if session.classification
                else None
            ),
            "symbolic_score": symbolic_score,
            "transcript": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "metadata": turn.metadata,
                }
                for turn in session.transcript
            ],
        }
        data = await self._generate_json(JUDGE_RUBRIC_PROMPT, payload)
        return JudgeRubricResult(
            reasoning_score=_score(data.get("reasoning_score"), default=0.5),
            citation_score=_score(data.get("citation_score"), default=0.5),
            resisted_pressure=bool(data.get("resisted_pressure", False)),
            feedback=str(data.get("feedback") or "Evaluacion generada."),
        )

    async def _generate_json(
        self,
        system_prompt: str,
        payload: dict[str, object],
    ) -> dict[str, Any]:
        user_prompt = json.dumps(payload, ensure_ascii=False, default=_json_default)
        raw = await self._llm.generate(system_prompt, user_prompt)
        parsed = _extract_json_object(raw)
        if parsed is not None:
            return parsed

        retry_prompt = (
            f"{user_prompt}\n\nLa respuesta anterior no fue JSON valido. "
            "Devuelve solo un objeto JSON valido, sin markdown."
        )
        raw = await self._llm.generate(system_prompt, retry_prompt)
        parsed = _extract_json_object(raw)
        return parsed or {}

    def _fallback_client(self, case: OperationCase) -> str:
        debtor = case.debtor_profile.get("nombre_deudor", "el deudor")
        return f"{debtor} solicita evaluar su operacion crediticia."

    def _fallback_supervisor(self, case: OperationCase) -> str:
        articles = ", ".join(case.justifying_articles) or "la norma recuperada"
        return f"Revise si su clasificacion se sustenta en {articles}."

    def _fallback_bank(self) -> str:
        return "El banco sugiere revisar si corresponde una categoria menor."


def _classification_payload(
    classification: Classification,
) -> dict[str, str]:
    return {
        "category": classification.category.value,
        "justification": classification.justification,
    }


def _chunk_payload(chunk: Chunk) -> dict[str, object]:
    return {
        "id": chunk.id,
        "label": chunk.numeral,
        "text": chunk.text,
        "chapter": chunk.chapter,
        "article": chunk.article,
        "topics": chunk.topics,
    }


def _risk_category_from_text(value: str) -> RiskCategory:
    normalized = value.strip().lower().replace("é", "e")
    for category in RiskCategory:
        if normalized == category.value.lower().replace("é", "e"):
            return category
    return RiskCategory.CPP


def _score(value: object, *, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _json_default(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return value.value
    return str(value)
