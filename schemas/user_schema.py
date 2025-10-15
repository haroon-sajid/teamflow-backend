# schemas/user_schema.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    is_invited: bool
    created_at: datetime
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"

class AccountActivate(BaseModel):
    token: str
    full_name: str
    password: str = Field(..., min_length=8)


