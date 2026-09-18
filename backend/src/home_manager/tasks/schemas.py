import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from home_manager.tasks.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    duration_minutes: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    preferred_start: datetime | None = None
    preferred_end: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)
    budget_amount: Decimal | None = Field(default=None, gt=0)
    # Whose money the budget draws from — null means shared/household.
    budget_owner_user_id: uuid.UUID | None = None
    # null means the default "My Tasks" bucket. Ignored when parent_task_id
    # is set — a subtask always inherits its parent's list.
    list_id: uuid.UUID | None = None
    # Set to make this task a subtask. Only one level of nesting is allowed —
    # the parent must not itself be a subtask (enforced in service.py).
    parent_task_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _validate_preferred_window(self) -> Self:
        if (
            self.preferred_start is not None
            and self.preferred_end is not None
            and self.preferred_end < self.preferred_start
        ):
            raise ValueError("preferred_end must not be before preferred_start")
        return self


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    preferred_start: datetime | None = None
    preferred_end: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)
    budget_amount: Decimal | None = Field(default=None, gt=0)
    budget_owner_user_id: uuid.UUID | None = None
    list_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    duration_minutes: int | None
    due_at: datetime | None
    preferred_start: datetime | None
    preferred_end: datetime | None
    location: str | None
    recurrence: str | None
    budget_amount: Decimal | None
    budget_owner_user_id: uuid.UUID | None
    list_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    order_index: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class TaskPageResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # Which member's section the folder is filed under — null (the default)
    # means the household's shared section. Every member sees every folder
    # either way; this only decides where it's grouped in the UI.
    owner_user_id: uuid.UUID | None = None


class TaskListUpdate(BaseModel):
    # Both optional so renaming and re-filing are independent — an unset
    # field is left alone, while an explicit null owner_user_id moves the
    # folder to the shared section.
    name: str | None = Field(default=None, min_length=1, max_length=100)
    owner_user_id: uuid.UUID | None = None


class TaskListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    owner_user_id: uuid.UUID | None
    name: str
    order_index: int
    created_at: datetime
    updated_at: datetime


class TaskListsResponse(BaseModel):
    items: list[TaskListResponse]


class TaskTemplateItem(BaseModel):
    """One node of a template's task tree. `children` nests the same shape,
    which is what gives the template its subtask structure."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    duration_minutes: int | None = Field(default=None, gt=0)
    children: list["TaskTemplateItem"] = Field(default_factory=list)


# Same cap as the tasks themselves (see MAX_TASK_DEPTH in service.py): a
# template that nested deeper could never be applied.
MAX_TEMPLATE_DEPTH = 4
MAX_TEMPLATE_ITEMS = 200


def _validate_tree(items: list[TaskTemplateItem], depth: int = 1) -> int:
    if items and depth >= MAX_TEMPLATE_DEPTH:
        raise ValueError(f"template nesting must not exceed {MAX_TEMPLATE_DEPTH} levels")
    count = 0
    for item in items:
        count += 1 + _validate_tree(item.children, depth + 1)
    return count


class TaskTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    list_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    duration_minutes: int | None = Field(default=None, gt=0)
    items: list[TaskTemplateItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_items(self) -> Self:
        if _validate_tree(self.items) > MAX_TEMPLATE_ITEMS:
            raise ValueError(f"a template must not hold more than {MAX_TEMPLATE_ITEMS} items")
        return self


class TaskTemplateCreate(TaskTemplateBase):
    pass


class TaskTemplateUpdate(TaskTemplateBase):
    """Saved whole, same as it's edited — the form always submits the full
    tree, so a partial update would only add ways for it to disagree with
    what's on screen."""


class TaskTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    list_id: uuid.UUID | None
    name: str
    description: str | None
    priority: TaskPriority
    duration_minutes: int | None
    items: list[TaskTemplateItem]
    created_at: datetime
    updated_at: datetime


class TaskTemplatesResponse(BaseModel):
    items: list[TaskTemplateResponse]


class TaskTemplateApplyRequest(BaseModel):
    """The one thing that differs per use — what this particular instance of
    the template is called (a track name, say)."""

    title: str = Field(min_length=1, max_length=200)
    due_at: datetime | None = None


class TaskReorderRequest(BaseModel):
    """Reorders one sibling group at once — every task sharing the same
    (list_id, parent_task_id) — rather than moving a single task to an
    index, since drag-and-drop UIs already know the full resulting order
    and this avoids any float/gap position math."""

    list_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    ordered_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class TaskListReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
