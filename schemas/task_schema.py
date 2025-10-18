# schemas/task_schema.py
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
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


# -------------------------------------------------------
# 🧱 Base Schema
# -------------------------------------------------------
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: str = Field(default="Open", max_length=20)
    priority: Optional[str] = Field(default="medium", max_length=20)
    due_date: Optional[datetime] = None
    project_id: int
    allow_member_edit: bool = Field(default=False)
    member_id: Optional[int] = None
    member_ids: Optional[List[int]] = None

    @field_validator("status")
    def normalize_status(cls, v):
        return _normalize_status(v)


# -------------------------------------------------------
# 🆕 Create
# -------------------------------------------------------
class TaskCreate(TaskBase):
    @model_validator(mode="after")
    def validate_member_fields(self):
        if self.member_id is None and (not self.member_ids or len(self.member_ids) == 0):
            raise ValueError("Either member_id or member_ids must be provided")
        return self


# -------------------------------------------------------
# ✏️ Update
# -------------------------------------------------------
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=20)
    priority: Optional[str] = Field(default=None, max_length=20)
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    allow_member_edit: Optional[bool] = None
    member_id: Optional[int] = None
    member_ids: Optional[List[int]] = None

    @field_validator("status")
    def normalize_status(cls, v):
        return _normalize_status(v) if v else v


# -------------------------------------------------------
# 🔐 Permission Update
# -------------------------------------------------------
class TaskPermissionUpdate(BaseModel):
    allow_member_edit: bool


# -------------------------------------------------------
# 💬 Comments
# -------------------------------------------------------
class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    message: str
    created_at: datetime
    user_name: str
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# ⏱ Work Logs
# -------------------------------------------------------
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
    user_name: str
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------
# 📤 Output Schema
# -------------------------------------------------------
class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    project_id: int
    organization_id: int
    allow_member_edit: bool = False
    created_at: datetime
    member_ids: Optional[List[int]] = None
    project_name: Optional[str] = None
    member_names: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)
