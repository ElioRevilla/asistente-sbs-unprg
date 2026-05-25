from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sbs_assistant.api.routes.example import router as example_router
from sbs_assistant.api.routes.explain import router as explain_router
from sbs_assistant.api.routes.health import router as health_router
from sbs_assistant.config.settings import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="SBS Assistant API", version="0.1.0")

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(explain_router)
    app.include_router(example_router)
    return app


app = create_app()
