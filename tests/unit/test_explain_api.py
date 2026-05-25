from fastapi.testclient import TestClient

from sbs_assistant.api.main import app
from sbs_assistant.api.routes.explain import get_explain_use_case
from sbs_assistant.application.use_cases.explain_concept import (
    Citation,
    ExplainConceptResult,
)


class FakeExplainUseCase:
    async def execute(self, request: object) -> ExplainConceptResult:
        return ExplainConceptResult(
            answer="CPP significa categoria con problemas potenciales (Numeral 3.2).",
            citations=[
                Citation(
                    chunk_id="sec_028_3_2",
                    label="Numeral 3.2",
                    text_preview="3.2 CATEGORIA CON PROBLEMAS POTENCIALES",
                )
            ],
        )


def test_explain_endpoint_returns_text_payload() -> None:
    app.dependency_overrides[get_explain_use_case] = lambda: FakeExplainUseCase()
    client = TestClient(app)

    response = client.post(
        "/modes/explain",
        json={"question": "Que es CPP?", "top_k": 3},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "type": "text",
        "data": {
            "answer": (
                "CPP significa categoria con problemas potenciales (Numeral 3.2)."
            ),
            "citations": [
                {
                    "chunk_id": "sec_028_3_2",
                    "label": "Numeral 3.2",
                    "text_preview": "3.2 CATEGORIA CON PROBLEMAS POTENCIALES",
                }
            ],
        },
    }


def test_explain_endpoint_validates_empty_question() -> None:
    app.dependency_overrides[get_explain_use_case] = lambda: FakeExplainUseCase()
    client = TestClient(app)

    response = client.post("/modes/explain", json={"question": ""})

    app.dependency_overrides.clear()
    assert response.status_code == 422
