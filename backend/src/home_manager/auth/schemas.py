import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from home_manager.auth.models import Gender, Role


class RegisterRequest(BaseModel):
    household_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    display_name: str
    role: Role
    gender: Gender | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
