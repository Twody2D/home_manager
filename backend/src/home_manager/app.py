from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from home_manager.api.v1 import api_router
from home_manager.config import get_settings
from home_manager.core.errors import register_exception_handlers
from home_manager.core.request_id import RequestIDMiddleware


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Home Manager API", version="0.1.0")

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
