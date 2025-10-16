# schemas/project_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    organization_id: Optional[int] = None

class ProjectRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    creator_id: int
    organization_id: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    organization_id: Optional[int] = None