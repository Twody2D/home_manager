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
from home_manager.tasks.schemas import (
    TaskCreate,
    TaskListCreate,
    TaskListReorderRequest,
    TaskListResponse,
    TaskListsResponse,
    TaskListUpdate,
    TaskPageResponse,
    TaskReorderRequest,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
task_lists_router = APIRouter(prefix="/task-lists", tags=["tasks"])

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


@router.get("", response_model=TaskPageResponse)
async def list_tasks(
    current_user: CurrentUser,
    session: DbSession,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    assigned_to: uuid.UUID | None = None,
    # Callers (TasksPage, TaskDetailPage) fetch the household's whole task
    # set in one page and build lists/subtask trees client-side — see
    # list_tasks below — so the cap here needs enough headroom that a task
    # count of a hundred-plus (a handful of trees a few levels deep) doesn't
    # silently truncate the response. 100 was too low: it clipped the tail
    # of the globally order_index-sorted result before some root-level
    # tasks in a household with many subtask trees, effectively hiding them
    # from the "Задачи" list while they still showed up everywhere that
    # doesn't paginate (the daily plan, subtask counts, etc).
    limit: Annotated[int, Query(ge=1, le=1000)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskPageResponse:
    items, total = await service.list_tasks(
        session,
        tenant_id=current_user.tenant_id,
        status_filter=status_filter,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    return TaskPageResponse(
        items=[TaskResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/reorder", response_model=list[TaskResponse])
async def reorder_tasks(
    payload: TaskReorderRequest, current_user: CurrentUser, session: DbSession
) -> list[TaskResponse]:
    # Registered before "/{task_id}" so "reorder" is never parsed as a
    # task id.
    tasks = await service.reorder_tasks(session, tenant_id=current_user.tenant_id, payload=payload)
    await session.commit()
    return [TaskResponse.model_validate(task) for task in tasks]


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


@task_lists_router.post("", response_model=TaskListResponse, status_code=status.HTTP_201_CREATED)
async def create_task_list(
    payload: TaskListCreate, current_user: CurrentUser, session: DbSession
) -> TaskListResponse:
    task_list = await service.create_task_list(
        session, tenant_id=current_user.tenant_id, created_by=current_user.id, payload=payload
    )
    await session.commit()
    return TaskListResponse.model_validate(task_list)


@task_lists_router.get("", response_model=TaskListsResponse)
async def list_task_lists(current_user: CurrentUser, session: DbSession) -> TaskListsResponse:
    items = await service.list_task_lists(session, tenant_id=current_user.tenant_id)
    return TaskListsResponse(items=[TaskListResponse.model_validate(item) for item in items])


@task_lists_router.patch("/reorder", response_model=list[TaskListResponse])
async def reorder_task_lists(
    payload: TaskListReorderRequest, current_user: CurrentUser, session: DbSession
) -> list[TaskListResponse]:
    # Registered before "/{list_id}" so "reorder" is never parsed as a
    # list id.
    lists = await service.reorder_task_lists(
        session, tenant_id=current_user.tenant_id, payload=payload
    )
    await session.commit()
    return [TaskListResponse.model_validate(task_list) for task_list in lists]


@task_lists_router.patch("/{list_id}", response_model=TaskListResponse)
async def update_task_list(
    list_id: uuid.UUID, payload: TaskListUpdate, current_user: CurrentUser, session: DbSession
) -> TaskListResponse:
    task_list = await service.update_task_list(
        session, tenant_id=current_user.tenant_id, list_id=list_id, payload=payload
    )
    await session.commit()
    return TaskListResponse.model_validate(task_list)


@task_lists_router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_list(
    list_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> None:
    await service.delete_task_list(session, tenant_id=current_user.tenant_id, list_id=list_id)
    await session.commit()
