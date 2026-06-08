from uuid import uuid4

import pytest

from sbs_assistant.application.services.debate_orchestrator import (
    MAX_ROUNDS,
    MIN_ROUNDS,
    DebateOrchestrator,
    InvalidSimulationTransitionError,
    should_close,
)
from sbs_assistant.domain.entities.agent_turn import (
    BancoTurnDTO,
    ClienteTurnDTO,
    SupervisorTurnDTO,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.debate_turn import DebateTurn
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import (
    SimulationSession,
    SimulationState,
)
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory
from sbs_assistant.domain.value_objects.verdict import Verdict


class FakeDebateAgents:
    def __init__(self, objections: list[bool] | None = None) -> None:
        self.objections = objections or [False]
        self.present_calls = 0
        self.challenge_calls = 0
        self.pressure_calls = 0
        self.prior_objections_seen: list[list[str]] = []

    async def present(self, case: OperationCase) -> ClienteTurnDTO:
        self.present_calls += 1
        credit_type = case.debtor_profile["tipo_credito"]
        return ClienteTurnDTO(narrative=f"Cliente presenta operacion {credit_type}")

    async def challenge(
        self,
        case: OperationCase,
        ground_truth: Classification,
        grounding_chunks: list[Chunk],
        last_defense: str | None,
        prior_objections: list[str],
    ) -> SupervisorTurnDTO:
        del case, grounding_chunks, last_defense
        self.challenge_calls += 1
        self.prior_objections_seen.append(prior_objections)
        index = min(self.challenge_calls - 1, len(self.objections) - 1)
        return SupervisorTurnDTO(
            challenge=(
                f"Objecion {self.challenge_calls}: debe revisar "
                f"{ground_truth.category.value}"
            ),
            objection_remaining=self.objections[index],
            cited_articles=["Capitulo II, numeral 3.3"],
        )

    async def pressure(
        self,
        case: OperationCase,
        current_classification: Classification,
    ) -> BancoTurnDTO:
        del case, current_classification
        self.pressure_calls += 1
        return BancoTurnDTO(
            pressure="El banco sugiere una categoria menor.",
            suggested_category=RiskCategory.CPP,
        )


class FakeJudge:
    def __init__(self) -> None:
        self.calls = 0
        self.evaluated_states: list[SimulationState] = []

    async def evaluate(self, session: SimulationSession) -> Verdict:
        self.calls += 1
        self.evaluated_states.append(session.state)
        return Verdict(
            final_category=session.case.ground_truth.category,
            is_correct=(
                session.classification.category == session.case.ground_truth.category
                if session.classification
                else False
            ),
            symbolic_score=1.0,
            reasoning_score=0.8,
            citation_score=0.8,
            resisted_pressure=True,
            overall=0.9,
            feedback="Veredicto de prueba.",
        )


class FakeRetriever:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        del filters
        self.queries.append(f"{query}|top_k={top_k}")
        return [
            Chunk(
                id="sec_027_3_3",
                text="3.3 Categoria Deficiente: atraso de 31 a 60 dias.",
                numeral="3.3",
            )
        ]


def make_session(state: SimulationState = SimulationState.PRESENT) -> SimulationSession:
    operation_case = OperationCase(
        id=uuid4(),
        cartera_type="minorista",
        debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
        narrative_hints={"tono": "simpatia"},
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Atraso de 31 a 60 dias.",
        ),
        justifying_articles=["Capitulo II, numeral 3.3"],
        case_type=CaseType.DETERMINABLE,
    )
    return SimulationSession(
        id=uuid4(),
        user_id="student-1",
        case=operation_case,
        state=state,
    )


def make_orchestrator(
    objections: list[bool] | None = None,
) -> tuple[DebateOrchestrator, FakeDebateAgents, FakeJudge, FakeRetriever]:
    agents = FakeDebateAgents(objections=objections)
    judge = FakeJudge()
    retriever = FakeRetriever()
    return (
        DebateOrchestrator(agents=agents, judge=judge, retriever=retriever),
        agents,
        judge,
        retriever,
    )


@pytest.mark.asyncio
async def test_present_case_moves_to_classify() -> None:
    orchestrator, agents, judge, retriever = make_orchestrator()

    session = await orchestrator.present_case(make_session())

    assert session.state == SimulationState.CLASSIFY
    assert session.transcript[-1].role == "cliente"
    assert agents.present_calls == 1
    assert judge.calls == 0
    assert retriever.queries == []


@pytest.mark.asyncio
async def test_classification_generates_challenge_and_bank_pressure() -> None:
    orchestrator, agents, judge, retriever = make_orchestrator(objections=[True])
    session = await orchestrator.present_case(make_session())

    challenged = await orchestrator.submit_classification(
        session,
        Classification(
            category=RiskCategory.CPP,
            justification="Creo que es CPP por los dias de atraso.",
        ),
    )

    assert challenged.state == SimulationState.DEFEND
    assert challenged.round == 1
    assert challenged.classification is not None
    assert [turn.role for turn in challenged.transcript] == [
        "cliente",
        "alumno",
        "supervisor",
        "banco",
    ]
    assert challenged.transcript[-2].metadata["objection_remaining"] is True
    assert agents.challenge_calls == 1
    assert agents.pressure_calls == 1
    assert "Deficiente" in retriever.queries[0]
    assert judge.calls == 0


@pytest.mark.asyncio
async def test_advance_defense_closes_when_supervisor_has_no_objection() -> None:
    orchestrator, agents, judge, _ = make_orchestrator(objections=[False])
    session = await orchestrator.present_case(make_session())
    challenged = await orchestrator.submit_classification(
        session,
        Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por atraso de 45 dias.",
        ),
    )

    closed = await orchestrator.advance_defense(
        challenged,
        defense="Mantengo Deficiente y cito el numeral 3.3.",
    )

    assert closed.state == SimulationState.CLOSED
    assert closed.verdict is not None
    assert closed.transcript[-1].role == "juez"
    assert judge.calls == 1
    assert judge.evaluated_states == [SimulationState.CLOSED]
    assert agents.challenge_calls == 1


@pytest.mark.asyncio
async def test_advance_defense_continues_without_repeating_prior_objections() -> None:
    orchestrator, agents, judge, _ = make_orchestrator(objections=[True, False])
    session = await orchestrator.present_case(make_session())
    challenged = await orchestrator.submit_classification(
        session,
        Classification(
            category=RiskCategory.CPP,
            justification="CPP por error.",
        ),
    )

    next_challenge = await orchestrator.advance_defense(
        challenged,
        defense="Defiendo mi criterio inicial.",
    )

    assert next_challenge.state == SimulationState.DEFEND
    assert next_challenge.round == 2
    assert next_challenge.verdict is None
    assert agents.challenge_calls == 2
    assert agents.prior_objections_seen[0] == []
    assert agents.prior_objections_seen[1] == ["Objecion 1: debe revisar Deficiente"]
    assert judge.calls == 0


@pytest.mark.asyncio
async def test_advance_defense_closes_at_max_rounds_even_with_objection() -> None:
    orchestrator, agents, judge, _ = make_orchestrator(objections=[True, True, True])
    session = await orchestrator.present_case(make_session())
    current = await orchestrator.submit_classification(
        session,
        Classification(
            category=RiskCategory.CPP,
            justification="CPP por error.",
        ),
    )
    for index in range(MAX_ROUNDS - 1):
        current = await orchestrator.advance_defense(
            current,
            defense=f"Defensa {index + 1}.",
        )

    closed = await orchestrator.advance_defense(
        current,
        defense="Ultima defensa.",
    )

    assert closed.state == SimulationState.CLOSED
    assert closed.round == MAX_ROUNDS
    assert judge.calls == 1
    assert agents.challenge_calls == MAX_ROUNDS


def test_should_close_respects_min_rounds_and_objection_flag() -> None:
    base = make_session(state=SimulationState.DEFEND)

    no_rounds = SimulationSession(
        id=base.id,
        user_id=base.user_id,
        case=base.case,
        state=SimulationState.DEFEND,
        round=MIN_ROUNDS - 1,
        transcript=[
            DebateTurn(
                role="supervisor",
                content="Sin objecion.",
                metadata={"objection_remaining": False},
            )
        ],
    )
    assert should_close(no_rounds) is False

    no_objection = SimulationSession(
        id=base.id,
        user_id=base.user_id,
        case=base.case,
        state=SimulationState.DEFEND,
        round=MIN_ROUNDS,
        transcript=[
            DebateTurn(
                role="supervisor",
                content="Sin objecion.",
                metadata={"objection_remaining": False},
            )
        ],
    )
    assert should_close(no_objection) is True

    still_objecting = SimulationSession(
        id=base.id,
        user_id=base.user_id,
        case=base.case,
        state=SimulationState.DEFEND,
        round=MIN_ROUNDS,
        transcript=[
            DebateTurn(
                role="supervisor",
                content="Aun hay objecion.",
                metadata={"objection_remaining": True},
            )
        ],
    )
    assert should_close(still_objecting) is False


@pytest.mark.asyncio
async def test_orchestrator_rejects_invalid_state_transition() -> None:
    orchestrator, _, _, _ = make_orchestrator()

    with pytest.raises(InvalidSimulationTransitionError):
        await orchestrator.present_case(make_session(state=SimulationState.DEFEND))
