from uuid import uuid4

from fastapi.testclient import TestClient

from sbs_assistant.api.main import app
from sbs_assistant.api.routes.example import get_example_repository
from sbs_assistant.domain.entities.case import SyntheticCase


class FakeSyntheticCaseRepository:
    def __init__(self) -> None:
        self.case_id = uuid4()
        self.saved_case: SyntheticCase | None = None

    async def save(self, case: SyntheticCase) -> SyntheticCase:
        self.saved_case = case
        return SyntheticCase(
            id=self.case_id,
            credit_type=case.credit_type,
            description=case.description,
            correct_category=case.correct_category,
            correct_provision=case.correct_provision,
            source_article=case.source_article,
            mode=case.mode,
        )

    async def get(self, case_id):
        if self.saved_case is None:
            return None
        return SyntheticCase(
            id=case_id,
            credit_type=self.saved_case.credit_type,
            description=self.saved_case.description,
            correct_category=self.saved_case.correct_category,
            correct_provision=self.saved_case.correct_provision,
            source_article=self.saved_case.source_article,
            mode=self.saved_case.mode,
        )


def test_generate_example_endpoint_returns_example_payload() -> None:
    repository = FakeSyntheticCaseRepository()
    app.dependency_overrides[get_example_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        "/modes/example/generate",
        json={"concept": "categoría Deficiente"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "example"
    assert payload["data"]["case_id"] == str(repository.case_id)
    assert payload["data"]["case"]["dias_atraso"] == 45
    assert "Deficiente" in payload["data"]["options"]


def test_answer_example_endpoint_returns_feedback_payload() -> None:
    repository = FakeSyntheticCaseRepository()
    app.dependency_overrides[get_example_repository] = lambda: repository
    client = TestClient(app)

    generated = client.post(
        "/modes/example/generate",
        json={"concept": "categoría Deficiente"},
    ).json()
    response = client.post(
        "/modes/example/answer",
        json={
            "case_id": generated["data"]["case_id"],
            "selected_category": "Deficiente",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["type"] == "example_feedback"
    assert response.json()["data"]["correct"] is True
