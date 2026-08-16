import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import User
from home_manager.core.errors import AppError
from home_manager.tasks.models import Task, TaskStatus
from home_manager.tasks.schemas import TaskCreate, TaskUpdate


class TaskNotFoundError(AppError):
    code = "TASK_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Task not found"


class InvalidAssigneeError(AppError):
    code = "INVALID_ASSIGNEE"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Assignee must be a member of the same household"


class InvalidTaskWindowError(AppError):
    code = "INVALID_TASK_WINDOW"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "preferred_end must not be before preferred_start"


class InvalidBudgetOwnerError(AppError):
    code = "INVALID_BUDGET_OWNER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Budget owner must be a member of the same household"


async def _ensure_assignee_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, assigned_to: uuid.UUID | None
) -> None:
    if assigned_to is None:
        return
    assignee = await session.get(User, assigned_to)
    if assignee is None or assignee.tenant_id != tenant_id:
        raise InvalidAssigneeError()


async def _ensure_budget_owner_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, budget_owner_user_id: uuid.UUID | None
) -> None:
    if budget_owner_user_id is None:
        return
    owner = await session.get(User, budget_owner_user_id)
    if owner is None or owner.tenant_id != tenant_id:
        raise InvalidBudgetOwnerError()


async def create_task(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, payload: TaskCreate
) -> Task:
    await _ensure_assignee_in_tenant(session, tenant_id=tenant_id, assigned_to=payload.assigned_to)
    await _ensure_budget_owner_in_tenant(
        session, tenant_id=tenant_id, budget_owner_user_id=payload.budget_owner_user_id
    )

    task = Task(
        tenant_id=tenant_id,
        created_by=created_by,
        assigned_to=payload.assigned_to,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        duration_minutes=payload.duration_minutes,
        due_at=payload.due_at,
        preferred_start=payload.preferred_start,
        preferred_end=payload.preferred_end,
        location=payload.location,
        recurrence=payload.recurrence,
        budget_amount=payload.budget_amount,
        budget_owner_user_id=payload.budget_owner_user_id,
    )
    session.add(task)
    await session.flush()
    return task


async def get_task(session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = await session.get(Task, task_id)
    if task is None or task.tenant_id != tenant_id:
        raise TaskNotFoundError()
    return task


async def list_tasks(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status_filter: TaskStatus | None,
    assigned_to: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Task], int]:
    query = select(Task).where(Task.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(Task).where(Task.tenant_id == tenant_id)

    if status_filter is not None:
        query = query.where(Task.status == status_filter)
        count_query = count_query.where(Task.status == status_filter)
    if assigned_to is not None:
        query = query.where(Task.assigned_to == assigned_to)
        count_query = count_query.where(Task.assigned_to == assigned_to)

    query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)

    total = await session.scalar(count_query)
    items = list((await session.scalars(query)).all())
    return items, total or 0


async def update_task(
    session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID, payload: TaskUpdate
) -> Task:
    task = await get_task(session, tenant_id=tenant_id, task_id=task_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "assigned_to" in updates:
        await _ensure_assignee_in_tenant(
            session, tenant_id=tenant_id, assigned_to=updates["assigned_to"]
        )
    if "budget_owner_user_id" in updates:
        await _ensure_budget_owner_in_tenant(
            session, tenant_id=tenant_id, budget_owner_user_id=updates["budget_owner_user_id"]
        )

    new_preferred_start = updates.get("preferred_start", task.preferred_start)
    new_preferred_end = updates.get("preferred_end", task.preferred_end)
    if (
        new_preferred_start is not None
        and new_preferred_end is not None
        and new_preferred_end < new_preferred_start
    ):
        raise InvalidTaskWindowError()

    for field, value in updates.items():
        setattr(task, field, value)

    if "status" in updates:
        task.completed_at = datetime.now(UTC) if updates["status"] == TaskStatus.COMPLETED else None

    await session.flush()
    return task


async def delete_task(session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = await get_task(session, tenant_id=tenant_id, task_id=task_id)
    await session.delete(task)
    await session.flush()
