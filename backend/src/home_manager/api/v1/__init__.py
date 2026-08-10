from fastapi import APIRouter

from home_manager.api.v1.health import router as health_router
from home_manager.auth.router import router as auth_router
from home_manager.calendar.router import router as calendar_router
from home_manager.preferences.router import router as preferences_router
from home_manager.tasks.router import router as tasks_router
from home_manager.users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(calendar_router)
api_router.include_router(preferences_router)
