import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NoteItem(BaseModel):
    """One bullet. `children` nests the same shape, so a note can hold
    sub-points and sub-sub-points."""

    text: str = Field(min_length=1, max_length=500)
    children: list["NoteItem"] = Field(default_factory=list)


# Same cap as tasks (MAX_TASK_DEPTH in tasks/service.py) so that any bullet
# can always be converted into a task tree without exceeding it.
MAX_NOTE_DEPTH = 4
MAX_NOTE_ITEMS = 500


def _validate_tree(items: list[NoteItem], depth: int = 1) -> int:
    if items and depth >= MAX_NOTE_DEPTH:
        raise ValueError(f"note nesting must not exceed {MAX_NOTE_DEPTH} levels")
    count = 0
    for item in items:
        count += 1 + _validate_tree(item.children, depth + 1)
    return count


class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    folder_id: uuid.UUID | None = None
    items: list[NoteItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_items(self) -> Self:
        if _validate_tree(self.items) > MAX_NOTE_ITEMS:
            raise ValueError(f"a note must not hold more than {MAX_NOTE_ITEMS} items")
        return self


class NoteCreate(NoteBase):
    pass


class NoteUpdate(NoteBase):
    """Saved whole, the same way the editor holds it."""


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    folder_id: uuid.UUID | None
    title: str
    items: list[NoteItem]
    order_index: int
    created_at: datetime
    updated_at: datetime


class NotesResponse(BaseModel):
    items: list[NoteResponse]


class NoteConvertRequest(BaseModel):
    """Turns one bullet — or the whole note, with an empty path — into a task
    plus a subtask per nested bullet."""

    # Chain of child indexes identifying the bullet; empty means the note
    # itself, whose title becomes the task and whose bullets become subtasks.
    path: list[int] = Field(default_factory=list, max_length=MAX_NOTE_DEPTH)
    list_id: uuid.UUID | None = None
    # Whether to drop the converted bullet from the note afterwards. Default
    # keeps it, since an idea list is also a record of what's been picked up.
    remove: bool = False


class NoteReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class NoteFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class NoteFolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class NoteFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    name: str
    order_index: int
    created_at: datetime
    updated_at: datetime


class NoteFoldersResponse(BaseModel):
    items: list[NoteFolderResponse]


class NoteFolderReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
