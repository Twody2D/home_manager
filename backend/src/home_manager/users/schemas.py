import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from home_manager.auth.models import Role


class MemberInviteRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.MEMBER


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    display_name: str
    role: Role


class InviteLinkResponse(BaseModel):
    token: str
    expires_at: datetime


class InvitePreviewResponse(BaseModel):
    household_name: str
    expires_at: datetime


class InviteRedeemRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class HouseholdResponse(BaseModel):
    name: str
    display_name: str | None


class HouseholdUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)


class MeUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
