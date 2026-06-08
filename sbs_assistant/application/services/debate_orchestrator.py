from dataclasses import replace
from datetime import UTC, datetime

from sbs_assistant.domain.entities.agent_turn import SupervisorTurnDTO
from sbs_assistant.domain.entities.debate_turn import DebateTurn
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
        grounding_chunks = await self._retriever.retrieve(
            self._grounding_query(session),
            top_k=GROUNDING_TOP_K,
        )
        prior_objections = self._prior_objections(session)
        supervisor_turn = await self._agents.challenge(
            case=session.case,
            ground_truth=session.case.ground_truth,
            grounding_chunks=grounding_chunks,
            last_defense=last_defense,
            prior_objections=prior_objections,
        )
        bank_turn = await self._agents.pressure(
            session.case,
            session.classification,
        )
        next_round = session.round + 1
        return replace(
            session,
            state=SimulationState.DEFEND,
            round=next_round,
            transcript=[
                *session.transcript,
                self._supervisor_turn(supervisor_turn),
                self._turn(
                    role="banco",
                    content=bank_turn.pressure,
                    metadata={
                        "suggested_category": bank_turn.suggested_category.value,
                    },
                ),
            ],
            updated_at=self._now(),
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
