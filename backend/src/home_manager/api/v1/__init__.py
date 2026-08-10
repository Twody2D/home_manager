from fastapi import APIRouter

from home_manager.api.v1.health import router as health_router
from home_manager.auth.router import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
