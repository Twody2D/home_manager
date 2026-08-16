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
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from home_manager.db.base import Base
from home_manager.db.types import utcnow


class SubscriptionCadence(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Income(Base):
    """A household member's recurring monthly income (e.g. salary).

    Belongs to exactly one user — income is inherently personal, unlike
    expenses — but is visible and editable by the whole household, since
    it's shared planning input, not a private log.
    """

    __tablename__ = "finance_incomes"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_finance_incomes_amount_positive"),
        CheckConstraint(
            "payment_day >= 1 AND payment_day <= 31", name="ck_finance_incomes_payment_day_valid"
        ),
        Index("ix_finance_incomes_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Day of month the income is received, 1-31 — months shorter than 31
    # days simply receive it on their last day (handled at read time, not
    # stored specially).
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )


class Subscription(Base):
    """A recurring monthly household payment (subscription, rent, etc.).

    owner_user_id is metadata only (whose name it's under / who's the
    contact for it) — it never affects any calculation, matching the
    household's shared-expense model.
    """

    __tablename__ = "finance_subscriptions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_finance_subscriptions_amount_positive"),
        CheckConstraint(
            "payment_day >= 1 AND payment_day <= 31",
            name="ck_finance_subscriptions_payment_day_valid",
        ),
        CheckConstraint(
            "(cadence = 'MONTHLY' AND payment_month IS NULL) "
            "OR (cadence = 'YEARLY' AND payment_month BETWEEN 1 AND 12)",
            name="ck_finance_subscriptions_payment_month_matches_cadence",
        ),
        Index("ix_finance_subscriptions_tenant_active", "tenant_id", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cadence: Mapped[SubscriptionCadence] = mapped_column(
        Enum(SubscriptionCadence, name="finance_subscription_cadence", native_enum=True),
        nullable=False,
        default=SubscriptionCadence.MONTHLY,
    )
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False)
    # Only set (and required) when cadence is yearly — which month the
    # once-a-year charge falls in. Null for monthly subscriptions.
    payment_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False
    )
