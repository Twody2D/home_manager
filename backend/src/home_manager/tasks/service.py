import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.models import User
from home_manager.core.errors import AppError
from home_manager.tasks.models import Task, TaskList, TaskPriority, TaskStatus, TaskTemplate
from home_manager.tasks.schemas import (
    TaskCreate,
    TaskListCreate,
    TaskListReorderRequest,
    TaskListUpdate,
    TaskReorderRequest,
    TaskTemplateApplyRequest,
    TaskTemplateCreate,
    TaskTemplateUpdate,
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


class TaskTemplateNotFoundError(AppError):
    code = "TASK_TEMPLATE_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Task template not found"


class InvalidTaskListOwnerError(AppError):
    code = "INVALID_TASK_LIST_OWNER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Folder owner must be a member of the same household"


class InvalidTaskListError(AppError):
    code = "INVALID_TASK_LIST"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "list_id must reference a list in the same household"


class InvalidParentTaskError(AppError):
    code = "INVALID_PARENT_TASK"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = (
        "parent_task_id must reference a task in the same household that doesn't exceed the "
        "nesting depth limit or create a cycle"
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


async def _ensure_list_owner_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, owner_user_id: uuid.UUID | None
) -> None:
    if owner_user_id is None:
        return
    owner = await session.get(User, owner_user_id)
    if owner is None or owner.tenant_id != tenant_id:
        raise InvalidTaskListOwnerError()


async def ensure_list_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, list_id: uuid.UUID | None
) -> None:
    if list_id is None:
        return
    task_list = await session.get(TaskList, list_id)
    if task_list is None or task_list.tenant_id != tenant_id:
        raise InvalidTaskListError()


# Levels: task / subtask / sub-subtask / sub-sub-subtask.
MAX_TASK_DEPTH = 4


async def _subtree_height(
    session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID
) -> int:
    """0 if task_id has no children, otherwise 1 + its tallest child subtree.

    Bounded by MAX_TASK_DEPTH in practice — every existing subtree already
    fits under the cap, so this recursion is never more than a few calls
    deep.
    """
    child_ids = list(
        (
            await session.scalars(
                select(Task.id).where(Task.tenant_id == tenant_id, Task.parent_task_id == task_id)
            )
        ).all()
    )
    if not child_ids:
        return 0
    heights = [
        await _subtree_height(session, tenant_id=tenant_id, task_id=child_id)
        for child_id in child_ids
    ]
    return 1 + max(heights)


async def _resolve_parent_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID | None,
    parent_task_id: uuid.UUID | None,
) -> Task | None:
    """Validates a subtask link and returns the parent (None if unset).

    Nesting is capped at MAX_TASK_DEPTH levels total. The task's new depth
    is its new parent's depth + 1; walking up the parent chain both counts
    that depth and rejects nesting a task under one of its own descendants
    (which would otherwise form a cycle). Whatever subtree of children the
    task already has (if any — relevant on move, since a fresh task never
    has children yet) must still fit under the cap at the new depth.
    """
    if parent_task_id is None:
        return None
    if parent_task_id == task_id:
        raise InvalidParentTaskError()
    parent = await session.get(Task, parent_task_id)
    if parent is None or parent.tenant_id != tenant_id:
        raise InvalidParentTaskError()

    ancestor: Task | None = parent
    parent_depth = 0
    while ancestor is not None:
        if task_id is not None and ancestor.id == task_id:
            raise InvalidParentTaskError()
        if ancestor.parent_task_id is None:
            break
        ancestor = await session.get(Task, ancestor.parent_task_id)
        parent_depth += 1

    new_depth = parent_depth + 1
    subtree_height = (
        await _subtree_height(session, tenant_id=tenant_id, task_id=task_id)
        if task_id is not None
        else 0
    )
    if new_depth + subtree_height > MAX_TASK_DEPTH - 1:
        raise InvalidParentTaskError()

    return parent


async def next_order_index(
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
        await ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=payload.list_id)
        list_id = payload.list_id
    order_index = await next_order_index(
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
            await ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=updates["list_id"])

    target_list_id = updates.get("list_id", task.list_id)
    target_parent_id = updates.get("parent_task_id", task.parent_task_id)
    if target_list_id != task.list_id or target_parent_id != task.parent_task_id:
        # Moved to a different sibling group (list and/or parent changed) —
        # append at the end of the new group rather than keeping a position
        # number that was only meaningful in the old one.
        updates["order_index"] = await next_order_index(
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
    await _ensure_list_owner_in_tenant(
        session, tenant_id=tenant_id, owner_user_id=payload.owner_user_id
    )
    order_index = (
        await session.scalar(
            select(func.coalesce(func.max(TaskList.order_index), -1) + 1).where(
                TaskList.tenant_id == tenant_id
            )
        )
        or 0
    )
    task_list = TaskList(
        tenant_id=tenant_id,
        created_by=created_by,
        owner_user_id=payload.owner_user_id,
        name=payload.name,
        order_index=order_index,
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
    updates = payload.model_dump(exclude_unset=True)
    if "owner_user_id" in updates:
        await _ensure_list_owner_in_tenant(
            session, tenant_id=tenant_id, owner_user_id=updates["owner_user_id"]
        )
    for field, value in updates.items():
        setattr(task_list, field, value)
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


async def create_task_template(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: TaskTemplateCreate,
) -> TaskTemplate:
    await ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=payload.list_id)
    template = TaskTemplate(
        tenant_id=tenant_id,
        created_by=created_by,
        list_id=payload.list_id,
        name=payload.name,
        description=payload.description,
        priority=payload.priority,
        duration_minutes=payload.duration_minutes,
        items=[item.model_dump(mode="json") for item in payload.items],
    )
    session.add(template)
    await session.flush()
    return template


async def list_task_templates(
    session: AsyncSession, *, tenant_id: uuid.UUID, list_id: uuid.UUID | None, list_id_set: bool
) -> list[TaskTemplate]:
    query = select(TaskTemplate).where(TaskTemplate.tenant_id == tenant_id)
    if list_id_set:
        query = query.where(
            TaskTemplate.list_id == list_id
            if list_id is not None
            else TaskTemplate.list_id.is_(None)
        )
    return list((await session.scalars(query.order_by(TaskTemplate.created_at.asc()))).all())


async def get_task_template(
    session: AsyncSession, *, tenant_id: uuid.UUID, template_id: uuid.UUID
) -> TaskTemplate:
    template = await session.get(TaskTemplate, template_id)
    if template is None or template.tenant_id != tenant_id:
        raise TaskTemplateNotFoundError()
    return template


async def update_task_template(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: TaskTemplateUpdate,
) -> TaskTemplate:
    template = await get_task_template(session, tenant_id=tenant_id, template_id=template_id)
    await ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=payload.list_id)
    template.name = payload.name
    template.list_id = payload.list_id
    template.description = payload.description
    template.priority = payload.priority
    template.duration_minutes = payload.duration_minutes
    template.items = [item.model_dump(mode="json") for item in payload.items]
    await session.flush()
    return template


async def delete_task_template(
    session: AsyncSession, *, tenant_id: uuid.UUID, template_id: uuid.UUID
) -> None:
    template = await get_task_template(session, tenant_id=tenant_id, template_id=template_id)
    await session.delete(template)
    await session.flush()


async def apply_task_template(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    template_id: uuid.UUID,
    payload: TaskTemplateApplyRequest,
) -> Task:
    """Creates the template's whole tree in one go and returns its root task.

    Building the tree server-side (rather than one request per node from the
    browser) keeps a 20-node template a single atomic operation: it either
    all lands or none of it does.
    """
    template = await get_task_template(session, tenant_id=tenant_id, template_id=template_id)
    order_index = await next_order_index(
        session, tenant_id=tenant_id, list_id=template.list_id, parent_task_id=None
    )
    root = Task(
        tenant_id=tenant_id,
        created_by=created_by,
        # Whoever applies the template owns what comes out of it, same
        # default as adding a task by hand.
        assigned_to=created_by,
        budget_owner_user_id=created_by,
        title=payload.title,
        description=template.description,
        status=TaskStatus.PENDING,
        priority=template.priority,
        duration_minutes=template.duration_minutes,
        due_at=payload.due_at,
        list_id=template.list_id,
        parent_task_id=None,
        order_index=order_index,
    )
    session.add(root)
    await session.flush()

    async def add_children(items: list[dict[str, Any]], parent: Task) -> None:
        for index, item in enumerate(items):
            child = Task(
                tenant_id=tenant_id,
                created_by=created_by,
                assigned_to=created_by,
                budget_owner_user_id=created_by,
                title=item["title"],
                description=item.get("description"),
                status=TaskStatus.PENDING,
                priority=item.get("priority", TaskPriority.MEDIUM),
                duration_minutes=item.get("duration_minutes"),
                list_id=template.list_id,
                parent_task_id=parent.id,
                order_index=index,
            )
            session.add(child)
            await session.flush()
            await add_children(item.get("children") or [], child)

    await add_children(template.items, root)
    return root


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
