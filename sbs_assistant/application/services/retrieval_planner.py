import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class PlannedAnswer(StrEnum):
    """Deterministic answer strategies for common regulatory questions."""

    CREDIT_TYPES = "credit_types"
    LONG_STAY_RISK_CATEGORY = "long_stay_risk_category"


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    """Internal retrieval plan derived from the student's question."""

    top_k: int
    query: str | None = None
    answer_strategy: PlannedAnswer | None = None


class RetrievalPlanner:
    """Plan retrieval settings behind the API surface."""

    def plan(self, question: str, requested_top_k: int) -> RetrievalPlan:
        if self._asks_for_credit_types(question):
            return RetrievalPlan(
                top_k=max(requested_top_k, 10),
                query=question,
                answer_strategy=PlannedAnswer.CREDIT_TYPES,
            )
        if self._asks_for_long_stay_risk_category(question):
            return RetrievalPlan(
                top_k=max(requested_top_k, 10),
                query=(
                    "permanezcan clasificados categoría Dudoso más de 36 meses "
                    "categoría Pérdida más de 24 meses Tabla 1 provisiones"
                ),
                answer_strategy=PlannedAnswer.LONG_STAY_RISK_CATEGORY,
            )
        return RetrievalPlan(top_k=requested_top_k)

    def _asks_for_credit_types(self, question: str) -> bool:
        normalized = self._normalize(question)
        asks_count = any(term in normalized for term in ["cuantos", "cuantas"])
        asks_count = asks_count or normalized.lstrip(" ¿?¡!").startswith("cu")
        asks_list = any(
            term in normalized
            for term in ["cuales son", "lista", "enumera", "menciona"]
        )
        mentions_credit_types = (
            "tipos de credito" in normalized
            or "tipo de credito" in normalized
            or "cartera de creditos" in normalized
            or "tipos de cr" in normalized
            or "tipo de cr" in normalized
            or "cartera de cr" in normalized
        )
        return mentions_credit_types and (asks_count or asks_list)

    def _asks_for_long_stay_risk_category(self, question: str) -> bool:
        normalized = self._normalize(question)
        mentions_risk_category = any(
            term in normalized for term in ["perdida", "dudoso"]
        )
        mentions_stay = any(
            term in normalized
            for term in [
                "permanece",
                "permanecen",
                "permanezcan",
                "mucho tiempo",
                "meses",
                "regla especial",
                "tiempo en categoria",
            ]
        )
        mentions_provision = "provision" in normalized or "provisiones" in normalized
        return mentions_risk_category and (mentions_stay or mentions_provision)

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        return without_accents.lower()
