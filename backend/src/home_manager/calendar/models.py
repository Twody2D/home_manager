import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from home_manager.db.base import Base
from home_manager.db.types import utcnow


class CalendarEventType(StrEnum):
    WORKING_HOURS = "working_hours"
    SLEEP = "sleep"
    MEETING = "meeting"
    SPORT = "sport"
    TRIP = "trip"
    PERSONAL = "personal"
    UNAVAILABLE = "unavailable"


class CalendarEvent(Base):
    """A block of a single user's schedule (their own calendar entry).

    Visible to the whole household (for availability checks) but only
    editable by the user it belongs to — see calendar/service.py.
    """

    __tablename__ = "calendar_events"
    __table_args__ = (
        CheckConstraint("end_at >= start_at", name="ck_calendar_events_end_after_start"),
        Index("ix_calendar_events_tenant_user_start", "tenant_id", "user_id", "start_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType, name="calendar_event_type", native_enum=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Raw recurrence rule, not yet interpreted — see the identical note on
    # tasks.models.Task.recurrence; the Planning Engine will define its format.
    recurrence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )
