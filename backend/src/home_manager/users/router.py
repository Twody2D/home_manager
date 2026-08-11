from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user, require_role
from home_manager.auth.models import Role, User
from home_manager.db.session import get_db_session
from home_manager.users import service
from home_manager.users.schemas import (
    HouseholdResponse,
    HouseholdUpdateRequest,
    InviteLinkResponse,
    InvitePreviewResponse,
    MemberInviteRequest,
    MemberResponse,
)

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=list[MemberResponse])
async def list_members(
    current_user: Annotated[User, Depends(get_current_user)], session: DbSession
) -> list[MemberResponse]:
    members = await service.list_members(session, tenant_id=current_user.tenant_id)
    return [MemberResponse.model_validate(member) for member in members]


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: MemberInviteRequest,
    current_user: Annotated[User, Depends(require_role(Role.OWNER))],
    session: DbSession,
) -> MemberResponse:
    member = await service.invite_member(
        session,
        tenant_id=current_user.tenant_id,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        role=payload.role,
    )
    await session.commit()
    return MemberResponse.model_validate(member)


@router.post("/invites", response_model=InviteLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_invite_link(
    current_user: Annotated[User, Depends(require_role(Role.OWNER))],
    session: DbSession,
) -> InviteLinkResponse:
    invite, raw_token = await service.create_invite(
        session, tenant_id=current_user.tenant_id, created_by=current_user.id
    )
    await session.commit()
    return InviteLinkResponse(token=raw_token, expires_at=invite.expires_at)


@router.get("/invites/{token}", response_model=InvitePreviewResponse)
async def preview_invite_link(token: str, session: DbSession) -> InvitePreviewResponse:
    invite, tenant_name = await service.preview_invite(session, raw_token=token)
    return InvitePreviewResponse(household_name=tenant_name, expires_at=invite.expires_at)


@router.get("/household", response_model=HouseholdResponse)
async def get_household(
    current_user: Annotated[User, Depends(get_current_user)], session: DbSession
) -> HouseholdResponse:
    tenant = await service.get_household(session, tenant_id=current_user.tenant_id)
    return HouseholdResponse(name=tenant.name, display_name=tenant.display_name)


@router.patch("/household", response_model=HouseholdResponse)
async def update_household(
    payload: HouseholdUpdateRequest,
    current_user: Annotated[User, Depends(require_role(Role.OWNER))],
    session: DbSession,
) -> HouseholdResponse:
    tenant = await service.update_household_display_name(
        session, tenant_id=current_user.tenant_id, display_name=payload.display_name
    )
    await session.commit()
    return HouseholdResponse(name=tenant.name, display_name=tenant.display_name)
