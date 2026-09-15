import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import User
from home_manager.core.errors import AppError
from home_manager.tasks.models import Task, TaskList, TaskStatus
from home_manager.tasks.schemas import (
    TaskCreate,
    TaskListCreate,
    TaskListReorderRequest,
    TaskListUpdate,
    TaskReorderRequest,
    TaskUpdate,
)


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


class TaskListNotFoundError(AppError):
    code = "TASK_LIST_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Task list not found"


class InvalidTaskListError(AppError):
    code = "INVALID_TASK_LIST"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "list_id must reference a list in the same household"


class InvalidParentTaskError(AppError):
    code = "INVALID_PARENT_TASK"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = (
        "parent_task_id must reference a top-level task in the same household with no "
        "subtasks of its own"
    )


class InvalidReorderError(AppError):
    code = "INVALID_REORDER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "ordered_ids must exactly match the current tasks in that list/subtask group"


class InvalidListReorderError(AppError):
    code = "INVALID_LIST_REORDER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "ordered_ids must exactly match the household's current task lists"


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


async def _ensure_list_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, list_id: uuid.UUID | None
) -> None:
    if list_id is None:
        return
    task_list = await session.get(TaskList, list_id)
    if task_list is None or task_list.tenant_id != tenant_id:
        raise InvalidTaskListError()


async def _resolve_parent_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID | None,
    parent_task_id: uuid.UUID | None,
) -> Task | None:
    """Validates a subtask link and returns the parent (None if unset).

    Nesting is capped at three levels total — task, subtask, sub-subtask —
    one level deeper than Google Tasks. A task becoming a sub-subtask (its
    new parent is itself a subtask) is only allowed when that parent's own
    parent is top-level (caps total depth) and the task has no children of
    its own (a sub-subtask can't have further children, which would exceed
    the cap). A task becoming an ordinary subtask (its new parent is
    top-level) is unrestricted either way — it may already have children,
    which simply become sub-subtasks.
    """
    if parent_task_id is None:
        return None
    if parent_task_id == task_id:
        raise InvalidParentTaskError()
    parent = await session.get(Task, parent_task_id)
    if parent is None or parent.tenant_id != tenant_id:
        raise InvalidParentTaskError()

    if parent.parent_task_id is not None:
        grandparent = await session.get(Task, parent.parent_task_id)
        if grandparent is not None and grandparent.parent_task_id is not None:
            raise InvalidParentTaskError()
        if task_id is not None:
            has_children = await session.scalar(
                select(func.count()).select_from(Task).where(Task.parent_task_id == task_id)
            )
            if has_children:
                raise InvalidParentTaskError()
    return parent


async def _next_order_index(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    list_id: uuid.UUID | None,
    parent_task_id: uuid.UUID | None,
) -> int:
    query = select(func.coalesce(func.max(Task.order_index), -1) + 1).where(
        Task.tenant_id == tenant_id,
        Task.list_id == list_id if list_id is not None else Task.list_id.is_(None),
        Task.parent_task_id == parent_task_id
        if parent_task_id is not None
        else Task.parent_task_id.is_(None),
    )
    return await session.scalar(query) or 0


async def create_task(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, payload: TaskCreate
) -> Task:
    await _ensure_assignee_in_tenant(session, tenant_id=tenant_id, assigned_to=payload.assigned_to)
    await _ensure_budget_owner_in_tenant(
        session, tenant_id=tenant_id, budget_owner_user_id=payload.budget_owner_user_id
    )
    parent = await _resolve_parent_task(
        session, tenant_id=tenant_id, task_id=None, parent_task_id=payload.parent_task_id
    )
    if parent is not None:
        list_id = parent.list_id
    else:
        await _ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=payload.list_id)
        list_id = payload.list_id
    order_index = await _next_order_index(
        session, tenant_id=tenant_id, list_id=list_id, parent_task_id=payload.parent_task_id
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
        list_id=list_id,
        parent_task_id=payload.parent_task_id,
        order_index=order_index,
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

    # Callers group into lists/subtask trees client-side from the full set —
    # same approach as the calendar day-list grouping — so no list_id filter
    # here; a household's task count is small enough that this is cheap.
    # order_index is only meaningful within one sibling group, so this
    # ordering is just a reasonable default — callers still sort each group
    # by order_index themselves once grouped.
    query = (
        query.order_by(Task.order_index.asc(), Task.created_at.desc()).limit(limit).offset(offset)
    )

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
    if "parent_task_id" in updates:
        parent = await _resolve_parent_task(
            session,
            tenant_id=tenant_id,
            task_id=task.id,
            parent_task_id=updates["parent_task_id"],
        )
        # A subtask always lives in its parent's list; promoting a subtask
        # back to top-level (parent_task_id -> null) leaves list_id as-is
        # unless the caller also set it explicitly in this same request.
        if parent is not None:
            updates["list_id"] = parent.list_id
    elif "list_id" in updates:
        if task.parent_task_id is not None:
            # Subtasks always inherit their parent's list — a bare list_id
            # change is a no-op rather than an error, same as if the field
            # had been left unset.
            del updates["list_id"]
        else:
            await _ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=updates["list_id"])

    target_list_id = updates.get("list_id", task.list_id)
    target_parent_id = updates.get("parent_task_id", task.parent_task_id)
    if target_list_id != task.list_id or target_parent_id != task.parent_task_id:
        # Moved to a different sibling group (list and/or parent changed) —
        # append at the end of the new group rather than keeping a position
        # number that was only meaningful in the old one.
        updates["order_index"] = await _next_order_index(
            session, tenant_id=tenant_id, list_id=target_list_id, parent_task_id=target_parent_id
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


async def reorder_tasks(
    session: AsyncSession, *, tenant_id: uuid.UUID, payload: TaskReorderRequest
) -> list[Task]:
    """Sets order_index for every task in one sibling group at once.

    ordered_ids must be exactly the current set of siblings — no more, no
    less. Requiring an exact match (rather than allowing a partial list)
    means the tenant_id-scoped fetch below is also the complete authorization
    check: an id from another household, or one that belongs to a different
    list/parent, simply won't be in the fetched set, so the set comparison
    fails closed instead of silently reordering a subset.
    """
    query = select(Task).where(
        Task.tenant_id == tenant_id,
        Task.list_id == payload.list_id if payload.list_id is not None else Task.list_id.is_(None),
        Task.parent_task_id == payload.parent_task_id
        if payload.parent_task_id is not None
        else Task.parent_task_id.is_(None),
    )
    siblings = {task.id: task for task in (await session.scalars(query)).all()}
    if set(payload.ordered_ids) != set(siblings.keys()):
        raise InvalidReorderError()

    for index, task_id in enumerate(payload.ordered_ids):
        siblings[task_id].order_index = index
    await session.flush()
    return [siblings[task_id] for task_id in payload.ordered_ids]


async def create_task_list(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, payload: TaskListCreate
) -> TaskList:
    order_index = (
        await session.scalar(
            select(func.coalesce(func.max(TaskList.order_index), -1) + 1).where(
                TaskList.tenant_id == tenant_id
            )
        )
        or 0
    )
    task_list = TaskList(
        tenant_id=tenant_id, created_by=created_by, name=payload.name, order_index=order_index
    )
    session.add(task_list)
    await session.flush()
    return task_list


async def list_task_lists(session: AsyncSession, *, tenant_id: uuid.UUID) -> list[TaskList]:
    query = (
        select(TaskList)
        .where(TaskList.tenant_id == tenant_id)
        .order_by(TaskList.order_index.asc(), TaskList.created_at.asc())
    )
    return list((await session.scalars(query)).all())


async def get_task_list(
    session: AsyncSession, *, tenant_id: uuid.UUID, list_id: uuid.UUID
) -> TaskList:
    task_list = await session.get(TaskList, list_id)
    if task_list is None or task_list.tenant_id != tenant_id:
        raise TaskListNotFoundError()
    return task_list


async def update_task_list(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    payload: TaskListUpdate,
) -> TaskList:
    task_list = await get_task_list(session, tenant_id=tenant_id, list_id=list_id)
    task_list.name = payload.name
    await session.flush()
    return task_list


async def delete_task_list(
    session: AsyncSession, *, tenant_id: uuid.UUID, list_id: uuid.UUID
) -> None:
    task_list = await get_task_list(session, tenant_id=tenant_id, list_id=list_id)
    # Tasks in this list are NOT deleted — Task.list_id's ondelete="SET NULL"
    # moves them back to the default "My Tasks" bucket.
    await session.delete(task_list)
    await session.flush()


async def reorder_task_lists(
    session: AsyncSession, *, tenant_id: uuid.UUID, payload: TaskListReorderRequest
) -> list[TaskList]:
    """Same exact-match-set pattern as reorder_tasks: fetching every list
    scoped to this tenant and requiring the payload to cover exactly that
    set doubles as the authorization check."""
    query = select(TaskList).where(TaskList.tenant_id == tenant_id)
    lists = {task_list.id: task_list for task_list in (await session.scalars(query)).all()}
    if set(payload.ordered_ids) != set(lists.keys()):
        raise InvalidListReorderError()

    for index, list_id in enumerate(payload.ordered_ids):
        lists[list_id].order_index = index
    await session.flush()
    return [lists[list_id] for list_id in payload.ordered_ids]
