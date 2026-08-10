from datetime import datetime

from pydantic import BaseModel


class AliceLinkStatusResponse(BaseModel):
    linked: bool
    last_used_at: datetime | None


class AliceTokenResponse(BaseModel):
    token: str
    webhook_url: str
