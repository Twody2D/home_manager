from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    """Process is up. Does not check dependencies."""
    return {"status": "ok"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    """Process is up and its dependencies (database) are reachable."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
