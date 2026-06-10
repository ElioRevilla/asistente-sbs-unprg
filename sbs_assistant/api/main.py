from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sbs_assistant.api.routes.chat_history import router as chat_history_router
from sbs_assistant.api.routes.example import router as example_router
from sbs_assistant.api.routes.explain import router as explain_router
from sbs_assistant.api.routes.health import router as health_router
from sbs_assistant.api.routes.simulation import router as simulation_router
from sbs_assistant.api.routes.teacher import router as teacher_router
from sbs_assistant.config.settings import get_settings
from sbs_assistant.infrastructure.persistence.connection import close_pool


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
    app.include_router(chat_history_router)
    app.include_router(explain_router)
    app.include_router(example_router)
    app.include_router(simulation_router)
    app.include_router(teacher_router)

    @app.on_event("shutdown")
    async def shutdown_database_pool() -> None:
        await close_pool()

    return app


app = create_app()
