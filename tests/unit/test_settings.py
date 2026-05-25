import pytest
from pydantic import ValidationError

from sbs_assistant.config.settings import Settings


def test_settings_defaults_are_local() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.service_name == "sbs-assistant"
    assert settings.gcp_region == "us-central1"
    assert settings.vertex_ai_location == "us-central1"
    assert settings.gemini_flash_model == "gemini-2.5-flash"
    assert settings.gemini_pro_model == "gemini-2.5-pro"
    assert settings.embeddings_model == "text-embedding-005"
    assert settings.cors_origins == []


def test_settings_accept_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SERVICE_NAME", "custom-sbs")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,https://app.example")
    monkeypatch.setenv("FIREBASE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "firebase-demo")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.service_name == "custom-sbs"
    assert settings.firebase_auth_required is True
    assert settings.firebase_token_project_id == "firebase-demo"
    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://app.example",
    ]


def test_settings_reject_invalid_model_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_FLASH_MODEL", "not-a-gemini-model")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
