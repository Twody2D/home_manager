import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.notifications import service as notifications_service
from home_manager.tasks import service
from home_manager.tasks.models import TaskStatus
from home_manager.tasks.schemas import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, current_user: CurrentUser, session: DbSession
) -> TaskResponse:
    task = await service.create_task(
        session, tenant_id=current_user.tenant_id, created_by=current_user.id, payload=payload
    )
    await session.commit()

    if task.assigned_to is not None and task.assigned_to != current_user.id:
        await notifications_service.send_push(
            session,
            tenant_id=current_user.tenant_id,
            user_id=task.assigned_to,
            title="New task assigned",
            body=task.title,
        )

    return TaskResponse.model_validate(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    current_user: CurrentUser,
    session: DbSession,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    assigned_to: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    items, total = await service.list_tasks(
        session,
        tenant_id=current_user.tenant_id,
        status_filter=status_filter,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> TaskResponse:
    task = await service.get_task(session, tenant_id=current_user.tenant_id, task_id=task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, current_user: CurrentUser, session: DbSession
) -> TaskResponse:
    task = await service.update_task(
        session, tenant_id=current_user.tenant_id, task_id=task_id, payload=payload
    )
    await session.commit()
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID, current_user: CurrentUser, session: DbSession) -> None:
    await service.delete_task(session, tenant_id=current_user.tenant_id, task_id=task_id)
    await session.commit()
