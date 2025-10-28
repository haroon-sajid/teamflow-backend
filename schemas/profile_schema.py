# schemas/profile_schema.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# -------------------------------------------------------
# 📤 Profile Read (Response Schema)
# -------------------------------------------------------
class ProfileRead(BaseModel):
    full_name: str
    email: EmailStr
    # username: Optional[str] = None
    role: str
    department: Optional[str] = None
    job_title: Optional[str] = None
    profile_picture: Optional[str] = None
    phone_number: Optional[str] = None
    time_zone: Optional[str] = None
    date_joined: datetime
    bio: Optional[str] = None
    skills: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# ✏️ Profile Update (Request Schema)
# -------------------------------------------------------
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    phone_number: Optional[str] = None
    time_zone: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    profile_picture: Optional[str] = None
