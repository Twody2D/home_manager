import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IncomeCreate(BaseModel):
    user_id: uuid.UUID | None = None
    label: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)


class IncomeUpdate(BaseModel):
    user_id: uuid.UUID | None = None
    label: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)


class IncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    label: str
    amount: Decimal
    payment_day: int
    created_at: datetime
    updated_at: datetime


class IncomeListResponse(BaseModel):
    items: list[IncomeResponse]
    total: int
    limit: int
    offset: int


class SubscriptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    owner_user_id: uuid.UUID | None = None


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)
    owner_user_id: uuid.UUID | None = None
    active: bool | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    amount: Decimal
    payment_day: int
    owner_user_id: uuid.UUID | None
    active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]
    total: int
    limit: int
    offset: int
