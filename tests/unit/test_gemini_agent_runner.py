from uuid import uuid4

import pytest

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
from sbs_assistant.infrastructure.llm.gemini_agent_runner import GeminiAgentRunner


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_gemini_agent_runner_does_not_leak_truth_to_client_or_bank() -> None:
    llm = FakeLLM(
        responses=[
            '{"narrative": "Necesito apoyo con mi credito."}',
            '{"pressure": "Podria ser CPP.", "suggested_category": "CPP"}',
        ]
    )
    runner = GeminiAgentRunner(llm)
    case = _case()

    client_turn = await runner.present(case)
    bank_turn = await runner.pressure(
        case,
        Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por 45 dias.",
        ),
    )

    assert client_turn.narrative == "Necesito apoyo con mi credito."
    assert bank_turn.suggested_category == RiskCategory.CPP
    assert "ground_truth" not in llm.calls[0][1]
    assert "ground_truth" not in llm.calls[1][1]
    assert "justifying_articles" not in llm.calls[0][1]
    assert "justifying_articles" not in llm.calls[1][1]


@pytest.mark.asyncio
async def test_gemini_agent_runner_retries_invalid_json() -> None:
    llm = FakeLLM(
        responses=[
            "no es json",
            '{"challenge": "Revise numeral 3.3", '
            '"objection_remaining": false, '
            '"cited_articles": ["Numeral 3.3"]}',
        ]
    )
    runner = GeminiAgentRunner(llm)

    turn = await runner.challenge(
        case=_case(),
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por atraso.",
        ),
        grounding_chunks=[Chunk(id="sec_027_3_3", text="Deficiente 31 a 60.")],
        last_defense="Cito la norma.",
        prior_objections=[],
    )

    assert turn.challenge == "Revise numeral 3.3"
    assert turn.objection_remaining is False
    assert turn.cited_articles == ["Numeral 3.3"]
    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_gemini_agent_runner_builds_judge_rubric() -> None:
    llm = FakeLLM(
        responses=[
            '{"reasoning_score": 0.8, "citation_score": 0.7, '
            '"resisted_pressure": true, "feedback": "Buen sustento."}'
        ]
    )
    runner = GeminiAgentRunner(llm)

    result = await runner.evaluate_reasoning(_session(), symbolic_score=1.0)

    assert result.reasoning_score == 0.8
    assert result.citation_score == 0.7
    assert result.resisted_pressure is True
    assert result.feedback == "Buen sustento."


def _case() -> OperationCase:
    return OperationCase(
        id=uuid4(),
        cartera_type="minorista",
        debtor_profile={"tipo_credito": "microempresa", "dias_atraso": 45},
        narrative_hints={"tono": "preocupado"},
        ground_truth=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Deficiente por 45 dias.",
        ),
        justifying_articles=["Capitulo II, numeral 3.3"],
        case_type=CaseType.DETERMINABLE,
    )


def _session() -> SimulationSession:
    return SimulationSession(
        id=uuid4(),
        user_id="student-1",
        case=_case(),
        state=SimulationState.CLOSED,
        round=1,
        classification=Classification(
            category=RiskCategory.DEFICIENTE,
            justification="Cito Capitulo II, numeral 3.3.",
        ),
        transcript=[
            DebateTurn(role="banco", content="Podria ser CPP."),
            DebateTurn(role="alumno", content="Mantengo Deficiente."),
        ],
    )
