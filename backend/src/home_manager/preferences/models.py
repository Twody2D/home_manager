import uuid
from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from home_manager.db.base import Base
from home_manager.db.types import utcnow


class EnergyPattern(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    STEADY = "steady"


class UserPreferences(Base):
    """A user's own planning preferences — always self-managed, never set by
    another household member. One row per user.
    """

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
        CheckConstraint("task_speed_multiplier > 0", name="ck_user_preferences_speed_positive"),
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
    workplace: Mapped[str | None] = mapped_column(String(200), nullable=True)
    working_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    working_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    sleep_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    sleep_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    energy_pattern: Mapped[EnergyPattern] = mapped_column(
        Enum(EnergyPattern, name="energy_pattern", native_enum=True),
        nullable=False,
        default=EnergyPattern.STEADY,
    )
    # Relative multiplier the Planning Engine will apply to a task's estimated
    # duration for this user (1.0 = as estimated, 1.5 = takes 50% longer, ...).
    task_speed_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )
