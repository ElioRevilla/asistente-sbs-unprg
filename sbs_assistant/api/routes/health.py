from typing import Annotated

from fastapi import APIRouter, Depends

from sbs_assistant.api.schemas.response_schemas import HealthResponse
from sbs_assistant.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDependency) -> HealthResponse:
    """Return a minimal readiness response for local and Cloud Run checks."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
    )
