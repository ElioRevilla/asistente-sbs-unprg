from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from sbs_assistant.api.main import app
from sbs_assistant.api.routes.simulation import (
    SimulationDependencies,
    get_simulation_dependencies,
)
from sbs_assistant.application.services.debate_orchestrator import DebateOrchestrator
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
            debtor_profile={
                "tipo_credito": "microempresa",
                "dias_atraso": 45,
                "monto": 10000,
            },
            narrative_hints={"client_bias": "sesgo simpatico"},
            ground_truth=Classification(
                category=RiskCategory.DEFICIENTE,
                justification="Deficiente por atraso de 31 a 60 dias.",
            ),
            justifying_articles=["Capitulo II, numeral 3.3"],
            case_type=CaseType.DETERMINABLE,
        )


class FakeDebateAgents:
    async def present(self, case: OperationCase) -> ClienteTurnDTO:
        del case
        return ClienteTurnDTO(
            narrative="El cliente pide reconsiderar su clasificacion."
        )

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
            challenge="Explique por que 45 dias no es CPP.",
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
            pressure="El banco sugiere CPP para provisionar menos.",
            suggested_category=RiskCategory.CPP,
        )


class FakeJudge:
    async def evaluate(self, session: SimulationSession) -> Verdict:
        return Verdict(
            final_category=session.case.ground_truth.category,
            is_correct=(
                session.classification.category == session.case.ground_truth.category
                if session.classification is not None
                else False
            ),
            symbolic_score=1.0,
            reasoning_score=0.8,
            citation_score=0.9,
            resisted_pressure=True,
            overall=0.93,
            feedback="Veredicto emitido.",
        )


class FakeRetriever:
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[Chunk]:
        del query, top_k, filters
        return [Chunk(id="sec_027_3_3", text="Deficiente de 31 a 60 dias.")]


def test_simulation_api_flow_hides_truth_until_closed() -> None:
    repository = FakeSimulationRepository()
    orchestrator = DebateOrchestrator(
        agents=FakeDebateAgents(),
        judge=FakeJudge(),
        retriever=FakeRetriever(),
    )
    app.dependency_overrides[get_simulation_dependencies] = lambda: (
        SimulationDependencies(
            repository=repository,
            orchestrator=orchestrator,
            case_selector=FakeCaseSelector(),
        )
    )
    client = TestClient(app)

    started = client.post(
        "/modes/simulation/start",
        json={"student_id": "student-1", "focus": "microempresa Deficiente"},
    )

    assert started.status_code == 200
    start_payload = started.json()
    session_id = start_payload["data"]["id"]
    assert start_payload["type"] == "simulation"
    assert start_payload["data"]["state"] == "classify"
    assert start_payload["data"]["case"]["ground_truth"] is None
    assert start_payload["data"]["case"]["justifying_articles"] is None
    assert start_payload["data"]["transcript"][0]["role"] == "cliente"

    classified = client.post(
        f"/modes/simulation/{session_id}/classify",
        json={
            "category": "Deficiente",
            "justification": "Es Deficiente por 45 dias de atraso.",
        },
    )

    assert classified.status_code == 200
    classify_payload = classified.json()
    assert classify_payload["data"]["state"] == "defend"
    assert classify_payload["data"]["case"]["ground_truth"] is None
    assert classify_payload["data"]["transcript"][-2]["role"] == "supervisor"
    assert classify_payload["data"]["transcript"][-1]["role"] == "banco"

    loaded = client.get(f"/modes/simulation/{session_id}")
    assert loaded.status_code == 200
    assert loaded.json()["data"]["case"]["ground_truth"] is None

    closed = client.post(
        f"/modes/simulation/{session_id}/turn",
        json={"defense": "Mantengo Deficiente y cito el numeral 3.3."},
    )

    app.dependency_overrides.clear()
    assert closed.status_code == 200
    closed_payload = closed.json()
    assert closed_payload["data"]["state"] == "closed"
    assert closed_payload["data"]["case"]["ground_truth"] == {
        "category": "Deficiente",
        "justification": "Deficiente por atraso de 31 a 60 dias.",
    }
    assert closed_payload["data"]["case"]["justifying_articles"] == [
        "Capitulo II, numeral 3.3"
    ]
    assert closed_payload["data"]["verdict"]["final_category"] == "Deficiente"
    assert closed_payload["data"]["transcript"][-1]["role"] == "juez"


def test_simulation_api_rejects_invalid_category() -> None:
    repository = FakeSimulationRepository()
    orchestrator = DebateOrchestrator(
        agents=FakeDebateAgents(),
        judge=FakeJudge(),
        retriever=FakeRetriever(),
    )
    app.dependency_overrides[get_simulation_dependencies] = lambda: (
        SimulationDependencies(
            repository=repository,
            orchestrator=orchestrator,
            case_selector=FakeCaseSelector(),
        )
    )
    client = TestClient(app)
    session_id = client.post(
        "/modes/simulation/start",
        json={"student_id": "student-1"},
    ).json()["data"]["id"]

    response = client.post(
        f"/modes/simulation/{session_id}/classify",
        json={
            "category": "Categoria inventada",
            "justification": "No aplica.",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "Categoria de riesgo invalida" in response.json()["detail"]
