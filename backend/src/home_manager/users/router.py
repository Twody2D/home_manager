from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user, require_role
from home_manager.auth.models import Role, User
from home_manager.db.session import get_db_session
from home_manager.users import service
from home_manager.users.schemas import MemberInviteRequest, MemberResponse

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
