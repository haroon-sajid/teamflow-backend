# schemas/task_schema.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Union
from datetime import datetime

def _normalize_status(v: str) -> str:
    mapping = {
        "open": "Open",
        "todo": "To Do",
        "inprogress": "In Progress",
        "in-progress": "In Progress",
        "in progress": "In Progress",
        "qa": "In QA",
        "done": "Done"
    }
    normalized_key = v.strip().lower().replace(" ", "").replace("-", "")
    return mapping.get(normalized_key, v)

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: str = Field(default="Open", max_length=20)
    priority: Optional[str] = Field(default="medium", max_length=20)
    due_date: Optional[datetime] = None
    project_id: int
    organization_id: Optional[int] = None
    allow_member_edit: bool = Field(default=False)  # NEW: Permission field
    
    # Support both single member (backward compatibility) and multiple members
    member_id: Optional[int] = None  # For backward compatibility
    member_ids: Optional[List[int]] = None  # For multiple members

    @field_validator('status')
    def normalize_status(cls, v):
        return _normalize_status(v)

class TaskCreate(TaskBase):
    # For creation, we require at least one member field
    @model_validator(mode='after')
    def validate_member_fields(self):
        if self.member_id is None and (not self.member_ids or len(self.member_ids) == 0):
            raise ValueError("Either member_id or member_ids must be provided")
        return self

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=20)
    priority: Optional[str] = Field(default=None, max_length=20)
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    organization_id: Optional[int] = None
    allow_member_edit: Optional[bool] = None  # NEW: Permission field
    
    # Support both single and multiple member updates
    member_id: Optional[int] = None
    member_ids: Optional[List[int]] = None

    @field_validator('status')
    def normalize_status(cls, v):
        return _normalize_status(v) if v else v

class TaskPermissionUpdate(BaseModel):
    allow_member_edit: bool

class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class CommentOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    message: str
    created_at: datetime
    user_name: str  # Added for frontend display

    model_config = {"from_attributes": True}

class WorkLogCreate(BaseModel):
    hours: float = Field(..., gt=0)
    description: Optional[str] = Field(default=None, max_length=500)
    date: Optional[datetime] = None

class WorkLogOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    hours: float
    date: datetime
    description: Optional[str]
    created_at: datetime
    user_name: str  # Added for frontend display

    model_config = {"from_attributes": True}

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    project_id: int
    organization_id: Optional[int] = None
    allow_member_edit: bool = False  # NEW: Permission field
    created_at: datetime
    member_ids: Optional[List[int]] = None
    project_name: Optional[str] = None
    member_names: Optional[List[str]] = None

    model_config = {"from_attributes": True}