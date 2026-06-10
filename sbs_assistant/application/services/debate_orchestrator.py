import re
from dataclasses import replace
from datetime import UTC, datetime

from sbs_assistant.domain.entities.agent_turn import SupervisorTurnDTO
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.ports.debate_agent_port import DebateAgentPort
from sbs_assistant.domain.ports.judge_port import JudgePort
from sbs_assistant.domain.ports.retriever_port import RetrieverPort
from sbs_assistant.domain.value_objects.classification import Classification

MIN_ROUNDS = 1
MAX_ROUNDS = 3
GROUNDING_TOP_K = 5
GROUNDING_CANDIDATE_TOP_K = 12

_CARTERA_TOPIC_BY_TYPE = {
    "minorista": "cartera_minorista",
    "cartera minorista": "cartera_minorista",
    "no minorista": "cartera_no_minorista",
    "cartera no minorista": "cartera_no_minorista",
    "hipotecaria": "cartera_hipotecaria_vivienda",
    "hipotecario": "cartera_hipotecaria_vivienda",
    "hipotecaria vivienda": "cartera_hipotecaria_vivienda",
    "hipotecario vivienda": "cartera_hipotecaria_vivienda",
}


class InvalidSimulationTransitionError(ValueError):
    """Raised when a simulation action is not valid for the current state."""


class DebateOrchestrator:
    """Deterministic state machine for adversarial simulations."""

    def __init__(
        self,
        *,
        agents: DebateAgentPort,
        judge: JudgePort,
        retriever: RetrieverPort,
    ) -> None:
        self._agents = agents
        self._judge = judge
        self._retriever = retriever

    async def present_case(self, session: SimulationSession) -> SimulationSession:
        """Let the client present the case and move the session to classify."""
        self._ensure_state(session, SimulationState.PRESENT)
        client_turn = await self._agents.present(session.case)
        return replace(
            session,
            state=SimulationState.CLASSIFY,
            transcript=[
                *session.transcript,
                self._turn(role="cliente", content=client_turn.narrative),
            ],
            updated_at=self._now(),
        )

    async def submit_classification(
        self,
        session: SimulationSession,
        classification: Classification,
    ) -> SimulationSession:
        """Register the student's classification and start the challenge phase."""
        self._ensure_state(session, SimulationState.CLASSIFY)
        classified = replace(
            session,
            state=SimulationState.CHALLENGE,
            classification=classification,
            transcript=[
                *session.transcript,
                self._turn(
                    role="alumno",
                    content=classification.justification,
                    metadata={"category": classification.category.value},
                ),
            ],
            updated_at=self._now(),
        )
        return await self._add_challenge_turns(classified, last_defense=None)

    async def advance_defense(
        self,
        session: SimulationSession,
        defense: str,
    ) -> SimulationSession:
        """Register a defense and either close or generate a new challenge."""
        self._ensure_state(session, SimulationState.DEFEND)
        defended = replace(
            session,
            transcript=[
                *session.transcript,
                self._turn(role="alumno", content=defense),
            ],
            updated_at=self._now(),
        )
        if should_close(defended):
            return await self._close(defended)
        challenged = replace(defended, state=SimulationState.CHALLENGE)
        return await self._add_challenge_turns(challenged, last_defense=defense)

    async def _add_challenge_turns(
        self,
        session: SimulationSession,
        *,
        last_defense: str | None,
    ) -> SimulationSession:
        if session.classification is None:
            raise InvalidSimulationTransitionError(
                "classification is required before challenge"
            )
        grounding_chunks = await self._retrieve_grounding_chunks(session)
        prior_objections = self._prior_objections(session)
        supervisor_turn = await self._agents.challenge(
            case=session.case,
            ground_truth=session.case.ground_truth,
            grounding_chunks=grounding_chunks,
            last_defense=last_defense,
            prior_objections=prior_objections,
        )
        next_round = session.round + 1
        supervisor_appended = replace(
            session,
            state=SimulationState.DEFEND,
            round=next_round,
            transcript=[
                *session.transcript,
                self._supervisor_turn(supervisor_turn),
            ],
            updated_at=self._now(),
        )
        if (
            last_defense is not None
            and next_round >= MIN_ROUNDS
            and not supervisor_turn.objection_remaining
        ):
            return await self._close(supervisor_appended)

        bank_turn = await self._agents.pressure(
            session.case,
            session.classification,
        )
        return replace(
            supervisor_appended,
            state=SimulationState.DEFEND,
            transcript=[
                *supervisor_appended.transcript,
                self._turn(
                    role="banco",
                    content=bank_turn.pressure,
                    metadata={
                        "suggested_category": bank_turn.suggested_category.value,
                    },
                ),
            ],
        )

    async def _close(self, session: SimulationSession) -> SimulationSession:
        candidate = replace(
            session,
            state=SimulationState.CLOSED,
            updated_at=self._now(),
        )
        verdict = await self._judge.evaluate(candidate)
        return replace(
            candidate,
            verdict=verdict,
            transcript=[
                *candidate.transcript,
                self._turn(
                    role="juez",
                    content=verdict.feedback,
                    metadata={
                        "final_category": verdict.final_category.value,
                        "overall": verdict.overall,
                        "is_correct": verdict.is_correct,
                    },
                ),
            ],
            updated_at=self._now(),
        )

    def _grounding_query(self, session: SimulationSession) -> str:
        profile_values = " ".join(
            str(value) for value in session.case.debtor_profile.values()
        )
        articles = " ".join(session.case.justifying_articles)
        return (
            f"{session.case.cartera_type} "
            f"{session.case.ground_truth.category.value} "
            f"{profile_values} {articles}"
        ).strip()

    async def _retrieve_grounding_chunks(
        self,
        session: SimulationSession,
    ) -> list[Chunk]:
        query = self._grounding_query(session)
        filters = self._grounding_filters(session.case)
        chunks = await self._retriever.retrieve(
            query,
            top_k=GROUNDING_CANDIDATE_TOP_K,
            filters=filters,
        )
        if not chunks and filters:
            chunks = await self._retriever.retrieve(
                query,
                top_k=GROUNDING_CANDIDATE_TOP_K,
            )
        return self._prioritize_grounding_chunks(session.case, chunks)[:GROUNDING_TOP_K]

    def _grounding_filters(self, case: OperationCase) -> dict[str, object] | None:
        normalized = case.cartera_type.strip().lower()
        topic = _CARTERA_TOPIC_BY_TYPE.get(normalized)
        if topic is None:
            return None
        return {"temas": [topic]}

    def _prioritize_grounding_chunks(
        self,
        case: OperationCase,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        article_tokens = _article_tokens(case.justifying_articles)
        if not article_tokens:
            return chunks
        return sorted(
            chunks,
            key=lambda chunk: (
                0 if _chunk_matches_articles(chunk, article_tokens) else 1,
                chunk.id,
            ),
        )

    def _prior_objections(self, session: SimulationSession) -> list[str]:
        return [
            turn.content for turn in session.transcript if turn.role == "supervisor"
        ]

    def _supervisor_turn(self, turn: SupervisorTurnDTO) -> DebateTurn:
        return self._turn(
            role="supervisor",
            content=turn.challenge,
            metadata={
                "objection_remaining": turn.objection_remaining,
                "cited_articles": turn.cited_articles,
            },
        )

    def _turn(
        self,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> DebateTurn:
        return DebateTurn(
            role=role,
            content=content,
            metadata=metadata or {},
            created_at=self._now(),
        )

    def _ensure_state(
        self,
        session: SimulationSession,
        expected: SimulationState,
    ) -> None:
        if session.state != expected:
            raise InvalidSimulationTransitionError(
                f"expected state {expected.value}, got {session.state.value}"
            )

    def _now(self) -> datetime:
        return datetime.now(UTC)


def should_close(session: SimulationSession) -> bool:
    """Return whether the debate should close after a defense turn."""
    if session.round >= MAX_ROUNDS:
        return True
    if session.round < MIN_ROUNDS:
        return False
    supervisor_turn = last_supervisor_turn(session)
    if supervisor_turn is None:
        return False
    return not bool(supervisor_turn.metadata.get("objection_remaining", True))


def last_supervisor_turn(session: SimulationSession) -> DebateTurn | None:
    """Return the most recent supervisor turn in the transcript."""
    for turn in reversed(session.transcript):
        if turn.role == "supervisor":
            return turn
    return None


def _article_tokens(articles: list[str]) -> set[str]:
    tokens: set[str] = set()
    for article in articles:
        tokens.update(re.findall(r"\b\d+(?:\.\d+)*\b", article))
    return tokens


def _chunk_matches_articles(chunk: Chunk, article_tokens: set[str]) -> bool:
    candidates = [
        chunk.numeral or "",
        chunk.id,
        chunk.text[:120],
    ]
    return any(
        token in candidate for token in article_tokens for candidate in candidates
    )
