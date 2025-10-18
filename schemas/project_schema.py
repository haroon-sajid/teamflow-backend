# schemas/project_schema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# -------------------------------------------------------
# 🗂️ CREATE
# -------------------------------------------------------
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    # organization_id will be set automatically from the current user's organization


# -------------------------------------------------------
# 🗂️ READ
# -------------------------------------------------------
class ProjectRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    creator_id: int
    organization_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# 🗂️ UPDATE
# -------------------------------------------------------
class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    # organization_id cannot be changed after creation
