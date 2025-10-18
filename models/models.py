
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import UniqueConstraint
import uuid

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"

class TaskMemberLink(SQLModel, table=True):
    task_id: int = Field(foreign_key="task.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)

class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    slug: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    users: List["User"] = Relationship(back_populates="organization")
    projects: List["Project"] = Relationship(back_populates="organization")
    tasks: List["Task"] = Relationship(back_populates="organization")
    invitations: List["Invitation"] = Relationship(back_populates="organization")

class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_org_email"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    email: str = Field(index=True, max_length=100, nullable=False)  # removed unique=True
    password_hash: str = Field(nullable=False)
    role: str = Field(default=UserRole.MEMBER.value, max_length=20, index=True)
    is_active: bool = Field(default=True)
    is_invited: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    organization: Optional[Organization] = Relationship(back_populates="users")

    projects: List["Project"] = Relationship(back_populates="creator")
    tasks: List["Task"] = Relationship(back_populates="members", link_model=TaskMemberLink)
    sent_invitations: List["Invitation"] = Relationship(back_populates="sent_by")
    comments: List["TaskComment"] = Relationship(back_populates="user")
    work_logs: List["TaskWorkLog"] = Relationship(back_populates="user")

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(max_length=500, default=None)
    creator_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    organization: Optional[Organization] = Relationship(back_populates="projects")

    creator: User = Relationship(back_populates="projects")
    tasks: List["Task"] = Relationship(back_populates="project")

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(max_length=1000, default=None)
    status: str = Field(default="Open", max_length=20)
    priority: str = Field(default="medium", max_length=20)
    due_date: Optional[datetime] = None
    project_id: int = Field(foreign_key="project.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    allow_member_edit: bool = Field(default=False)

    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    organization: Optional[Organization] = Relationship(back_populates="tasks")

    project: Project = Relationship(back_populates="tasks")
    members: List[User] = Relationship(back_populates="tasks", link_model=TaskMemberLink)
    comments: List["TaskComment"] = Relationship(back_populates="task")
    work_logs: List["TaskWorkLog"] = Relationship(back_populates="task")

class TaskComment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    user_id: int = Field(foreign_key="user.id")
    message: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    task: Task = Relationship(back_populates="comments")
    user: User = Relationship(back_populates="comments")

class TaskWorkLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    user_id: int = Field(foreign_key="user.id")
    hours: float = Field(gt=0)
    description: Optional[str] = Field(max_length=500, default=None)
    date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    task: Task = Relationship(back_populates="work_logs")
    user: User = Relationship(back_populates="work_logs")

class Invitation(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_org_invite_email"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(max_length=100, nullable=False, index=True)
    token: str = Field(max_length=255, unique=True, nullable=False, index=True)
    role: str = Field(default=UserRole.MEMBER.value, max_length=20)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_by_id: int = Field(foreign_key="user.id")
    accepted: bool = Field(default=False)
    accepted_at: Optional[datetime] = None

    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    organization: Optional[Organization] = Relationship(back_populates="invitations")

    sent_by: User = Relationship(back_populates="sent_invitations")
