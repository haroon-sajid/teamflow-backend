# schemas/organization_schema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# -------------------------------------------------------
# 🏢 CREATE
# -------------------------------------------------------
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=50)
    # slug will be auto-generated from name if not provided


# -------------------------------------------------------
# 🏢 READ
# -------------------------------------------------------
class OrganizationRead(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# 🏢 UPDATE
# -------------------------------------------------------
class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=50)
