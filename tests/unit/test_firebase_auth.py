from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from sbs_assistant.api.auth import firebase as firebase_auth_module
from sbs_assistant.api.auth.firebase import FirebaseUser, get_current_user
from sbs_assistant.config.settings import Settings, get_settings


def _client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/me")
    async def me(
        user: Annotated[FirebaseUser | None, Depends(get_current_user)],
    ) -> dict[str, str | None]:
        return {"uid": user.uid if user else None}

    return TestClient(app)


def test_auth_dependency_allows_missing_token_when_auth_is_optional() -> None:
    client = _client(Settings(_env_file=None, FIREBASE_AUTH_REQUIRED=False))

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json() == {"uid": None}


def test_auth_dependency_rejects_missing_token_when_auth_is_required() -> None:
    client = _client(Settings(_env_file=None, FIREBASE_AUTH_REQUIRED=True))

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Firebase ID token."


def test_auth_dependency_accepts_valid_firebase_token(monkeypatch) -> None:
    monkeypatch.setattr(firebase_auth_module, "_get_firebase_app", lambda _: object())
    monkeypatch.setattr(
        firebase_auth_module.auth,
        "verify_id_token",
        lambda token, app, check_revoked: {
            "uid": "firebase-user-1",
            "email": "student@example.com",
            "name": "Student",
        },
    )
    client = _client(
        Settings(
            _env_file=None,
            FIREBASE_AUTH_REQUIRED=True,
            FIREBASE_PROJECT_ID="sbs-assistant-unprg",
        )
    )

    response = client.get("/me", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json() == {"uid": "firebase-user-1"}


def test_auth_dependency_rejects_invalid_firebase_token(monkeypatch) -> None:
    def raise_invalid_token(token, app, check_revoked):
        raise ValueError("invalid")

    monkeypatch.setattr(firebase_auth_module, "_get_firebase_app", lambda _: object())
    monkeypatch.setattr(
        firebase_auth_module.auth,
        "verify_id_token",
        raise_invalid_token,
    )
    client = _client(
        Settings(
            _env_file=None,
            FIREBASE_AUTH_REQUIRED=True,
            FIREBASE_PROJECT_ID="sbs-assistant-unprg",
        )
    )

    response = client.get("/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Firebase ID token."
