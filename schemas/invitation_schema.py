# schemas/invitation_schema.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", max_length=20)
    organization_id: Optional[int] = None

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
    organization_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class InvitationUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, max_length=20)
    organization_id: Optional[int] = None
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None