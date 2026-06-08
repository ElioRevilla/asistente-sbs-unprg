from uuid import UUID, uuid4

import pytest

from sbs_assistant.application.services.debate_orchestrator import (
    DebateOrchestrator,
)
from sbs_assistant.application.use_cases.advance_debate import (
    AdvanceDebateRequest,
    AdvanceDebateUseCase,
)
from sbs_assistant.application.use_cases.get_simulation import (
    GetSimulationRequest,
    GetSimulationUseCase,
)
from sbs_assistant.application.use_cases.start_simulation import (
    StartSimulationRequest,
    StartSimulationUseCase,
)
from sbs_assistant.application.use_cases.submit_classification import (
    SubmitClassificationRequest,
    SubmitClassificationUseCase,
)
from sbs_assistant.domain.entities.agent_turn import (
    BancoTurnDTO,
    ClienteTurnDTO,
    SupervisorTurnDTO,
)
from sbs_assistant.domain.entities.chunk import Chunk
from sbs_assistant.domain.entities.operation_case import OperationCase
from sbs_assistant.domain.entities.simulation_session import SimulationSession
from sbs_assistant.domain.value_objects.case_type import CaseType
from sbs_assistant.domain.value_objects.classification import Classification
from sbs_assistant.domain.value_objects.risk_category import RiskCategory
from sbs_assistant.domain.value_objects.verdict import Verdict


class FakeCaseSelector:
    async def next_case(
        self,
        user_id: str,
        focus: str | None = None,
    ) -> OperationCase:
        del user_id, focus
        return OperationCase(
            id=uuid4(),
            cartera_type="minorista",
            debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
            narrative_hints={"tono": "preocupado"},
            ground_truth=Classification(
                category=RiskCategory.DEFICIENTE,
                justification="Atraso de 31 a 60 dias.",
            ),
            justifying_articles=["Capitulo II, numeral 3.3"],
            case_type=CaseType.DETERMINABLE,
        )


class FakeSimulationRepository:
    def __init__(self) -> None:
        self.sessions: dict[UUID, SimulationSession] = {}

    async def create(self, session: SimulationSession) -> SimulationSession:
        self.sessions[session.id] = session
        return session

    async def get(self, session_id: UUID) -> SimulationSession | None:
        return self.sessions.get(session_id)

    async def update(self, session: SimulationSession) -> SimulationSession:
        self.sessions[session.id] = session
        return session

    async def list_by_user(self, user_id: str) -> list[SimulationSession]:
        return [
            session for session in self.sessions.values() if session.user_id == user_id
        ]


class FakeDebateAgents:
    async def present(self, case: OperationCase) -> ClienteTurnDTO:
        del case
        return ClienteTurnDTO(narrative="Necesito defender mi operacion.")

    async def challenge(
        self,
        case: OperationCase,
        ground_truth: Classification,
        grounding_chunks: list[Chunk],
        last_defense: str | None,
        prior_objections: list[str],
    ) -> SupervisorTurnDTO:
        del case, ground_truth, grounding_chunks, last_defense, prior_objections
        return SupervisorTurnDTO(
            challenge="Sustente el rango de dias segun la norma.",
            objection_remaining=False,
            cited_articles=["Capitulo II, numeral 3.3"],
        )

    async def pressure(
        self,
        case: OperationCase,
        current_classification: Classification,
    ) -> BancoTurnDTO:
        del case, current_classification
        return BancoTurnDTO(
            pressure="Podria ser CPP para provisionar menos.",
            suggested_category=RiskCategory.CPP,
        )


class FakeJudge:
    async def evaluate(self, session: SimulationSession) -> Verdict:
        return Verdict(
            final_category=session.case.ground_truth.category,
            is_correct=(
                session.classification.category == session.case.ground_truth.category
                if session.classification
                else False
            ),
            symbolic_score=1.0,
            reasoning_score=0.8,
            citation_score=0.9,
            resisted_pressure=True,
            overall=0.93,
            feedback="Clasificacion sustentada.",
        )


class FakeRetriever:
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        del query, top_k, filters
        return [Chunk(id="sec_027_3_3", text="Deficiente: 31 a 60 dias.")]


def make_use_cases() -> tuple[
    FakeSimulationRepository,
    StartSimulationUseCase,
    SubmitClassificationUseCase,
    AdvanceDebateUseCase,
    GetSimulationUseCase,
]:
    repository = FakeSimulationRepository()
    orchestrator = DebateOrchestrator(
        agents=FakeDebateAgents(),
        judge=FakeJudge(),
        retriever=FakeRetriever(),
    )
    return (
        repository,
        StartSimulationUseCase(
            case_selector=FakeCaseSelector(),
            repository=repository,
            orchestrator=orchestrator,
        ),
        SubmitClassificationUseCase(
            repository=repository,
            orchestrator=orchestrator,
        ),
        AdvanceDebateUseCase(
            repository=repository,
            orchestrator=orchestrator,
        ),
        GetSimulationUseCase(repository=repository),
    )


@pytest.mark.asyncio
async def test_simulation_use_cases_hide_truth_until_closed() -> None:
    _, start, classify, advance, get = make_use_cases()

    started = await start.execute(StartSimulationRequest(user_id="student-1"))

    assert started.state == "classify"
    assert started.case.ground_truth is None
    assert started.case.justifying_articles is None
    assert started.transcript[0].role == "cliente"

    challenged = await classify.execute(
        SubmitClassificationRequest(
            session_id=started.id,
            category="Deficiente",
            justification="Deficiente por 45 dias de atraso.",
        )
    )

    assert challenged.state == "defend"
    assert challenged.case.ground_truth is None
    assert challenged.case.justifying_articles is None
    assert challenged.classification is not None
    assert challenged.transcript[-2].role == "supervisor"
    assert challenged.transcript[-1].role == "banco"

    loaded = await get.execute(GetSimulationRequest(session_id=started.id))
    assert loaded.case.ground_truth is None

    closed = await advance.execute(
        AdvanceDebateRequest(
            session_id=started.id,
            defense="Mantengo Deficiente y cito el numeral 3.3.",
        )
    )

    assert closed.state == "closed"
    assert closed.case.ground_truth is not None
    assert closed.case.ground_truth.category == "Deficiente"
    assert closed.case.justifying_articles == ["Capitulo II, numeral 3.3"]
    assert closed.verdict is not None
    assert closed.transcript[-1].role == "juez"


@pytest.mark.asyncio
async def test_submit_classification_accepts_unaccented_perdida() -> None:
    _, start, classify, _, _ = make_use_cases()
    started = await start.execute(StartSimulationRequest(user_id="student-1"))

    result = await classify.execute(
        SubmitClassificationRequest(
            session_id=started.id,
            category="Perdida",
            justification="Creo que es perdida.",
        )
    )

    assert result.classification is not None
    assert result.classification.category == "Pérdida"


@pytest.mark.asyncio
async def test_get_simulation_raises_when_session_is_missing() -> None:
    repository = FakeSimulationRepository()
    use_case = GetSimulationUseCase(repository=repository)

    with pytest.raises(ValueError):
        await use_case.execute(GetSimulationRequest(session_id=uuid4()))
