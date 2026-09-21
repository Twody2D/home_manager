import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from home_manager.db.base import Base
from home_manager.db.types import utcnow


class Note(Base):
    """A free-form idea list — a title plus a nested bullet tree, kept apart
    from tasks so half-formed thoughts don't turn into things the planner
    thinks you owe it. Any bullet (or the whole note) can be turned into a
    task later.

    Like task templates, the tree lives in a JSON column: it's always read
    and saved as one document, never queried by individual bullet.
    """

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # List of nested item dicts — see NoteItem in schemas.py for the shape.
    items: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    # Manual sort position among a household's notes, newest-first by
    # default — same convention as Task.order_index.
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )
