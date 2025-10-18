# schemas/invitation_schema.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# -------------------------------------------------------
# 📩 CREATE (Admin invites a user)
# -------------------------------------------------------
class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", max_length=20)
    # organization_id will be assigned automatically from the inviter's org
    organization_id: Optional[int] = None


# -------------------------------------------------------
# 📩 READ (Full record, internal use)
# -------------------------------------------------------
class InvitationRead(BaseModel):
    id: int
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    created_at: datetime
    accepted: bool
    accepted_at: Optional[datetime] = None
    sent_by_id: int
    organization_id: int
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# 📩 UPDATE (Used by backend to mark accepted)
# -------------------------------------------------------
class InvitationUpdate(BaseModel):
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None
