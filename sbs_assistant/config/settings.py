from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    service_name: str = Field(default="sbs-assistant", validation_alias="SERVICE_NAME")
    sbs_pdf_url: str = Field(
        default=(
            "https://www.sbs.gob.pe/portals/0/jer/pfrpv_normatividad/"
            "20160719_res-11356-2008.pdf"
        ),
        validation_alias="SBS_PDF_URL",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        validation_alias="CORS_ORIGINS",
    )
    firebase_auth_required: bool = Field(
        default=False,
        validation_alias="FIREBASE_AUTH_REQUIRED",
    )
    firebase_project_id: str | None = Field(
        default=None,
        validation_alias="FIREBASE_PROJECT_ID",
    )

    gcp_project_id: str | None = Field(default=None, validation_alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", validation_alias="GCP_REGION")
    vertex_ai_location: str = Field(
        default="us-central1",
        validation_alias="VERTEX_AI_LOCATION",
    )

    cloudsql_instance: str | None = Field(
        default=None, validation_alias="CLOUDSQL_INSTANCE"
    )
    db_host: str | None = Field(default=None, validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str | None = Field(default=None, validation_alias="DB_NAME")
    db_user: str | None = Field(default=None, validation_alias="DB_USER")
    db_password: str | None = Field(default=None, validation_alias="DB_PASSWORD")

    gcs_bucket_docs: str | None = Field(
        default=None,
        validation_alias="GCS_BUCKET_DOCS",
    )

    gemini_flash_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_FLASH_MODEL",
    )
    gemini_pro_model: str = Field(
        default="gemini-2.5-pro",
        validation_alias="GEMINI_PRO_MODEL",
    )
    embeddings_model: str = Field(
        default="text-embedding-005",
        validation_alias="EMBEDDINGS_MODEL",
    )

    docai_processor_layout_id: str | None = Field(
        default=None,
        validation_alias="DOCAI_PROCESSOR_LAYOUT_ID",
    )
    docai_processor_form_id: str | None = Field(
        default=None,
        validation_alias="DOCAI_PROCESSOR_FORM_ID",
    )

    @property
    def postgres_host(self) -> str | None:
        """Return the configured PostgreSQL host."""
        return self.db_host

    @property
    def postgres_port(self) -> int:
        """Return the configured PostgreSQL port."""
        return self.db_port

    @property
    def postgres_database(self) -> str | None:
        """Return the configured PostgreSQL database name."""
        return self.db_name

    @property
    def postgres_user(self) -> str | None:
        """Return the configured PostgreSQL user."""
        return self.db_user

    @property
    def postgres_password(self) -> str | None:
        """Return the configured PostgreSQL password."""
        return self.db_password

    @property
    def cloudsql_instance_connection_name(self) -> str | None:
        """Return the Cloud SQL connection name when Cloud SQL is configured."""
        if not self.cloudsql_instance or not self.gcp_project_id:
            return None
        return f"{self.gcp_project_id}:{self.gcp_region}:{self.cloudsql_instance}"

    @property
    def firebase_token_project_id(self) -> str | None:
        """Return the Firebase project used to verify ID tokens."""
        return self.firebase_project_id or self.gcp_project_id

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Parse CORS origins from a comma-separated env var or a list."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        raise TypeError("CORS_ORIGINS must be a comma-separated string or a list")

    @field_validator("gemini_flash_model")
    @classmethod
    def validate_flash_model(cls, value: str) -> str:
        """Ensure the configured Flash model looks like a Gemini model."""
        if not value.startswith("gemini-"):
            raise ValueError("GEMINI_FLASH_MODEL must start with 'gemini-'")
        return value

    @field_validator("gemini_pro_model")
    @classmethod
    def validate_pro_model(cls, value: str) -> str:
        """Ensure the configured Pro model looks like a Gemini model."""
        if not value.startswith("gemini-"):
            raise ValueError("GEMINI_PRO_MODEL must start with 'gemini-'")
        return value

    @field_validator("embeddings_model")
    @classmethod
    def validate_embeddings_model(cls, value: str) -> str:
        """Ensure the embedding model keeps the expected 768-dim family."""
        if value != "text-embedding-005":
            raise ValueError("EMBEDDINGS_MODEL must be 'text-embedding-005'")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
