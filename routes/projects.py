# routes/projects.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from core.database import get_session
from models.models import Project, User
from schemas.project_schema import ProjectCreate, ProjectRead
from core.security import get_current_user

router = APIRouter(tags=["Projects"])

# --------------------------------------------------------
#   Create New Project with Organization
# --------------------------------------------------------
@router.post("/", response_model=ProjectRead)
def create_project(
    data: ProjectCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = Project(
        name=data.name,
        description=data.description,
        creator_id=current_user.id,
        organization_id=current_user.organization_id,  # ✅ Attach organization
        created_at=datetime.utcnow()
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

# --------------------------------------------------------
#   Get All Projects (filtered by organization)
# --------------------------------------------------------
@router.get("/", response_model=List[ProjectRead])
def get_projects(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # ✅ Only get projects from the user's organization
    projects = session.exec(
        select(Project).where(Project.organization_id == current_user.organization_id)
        .order_by(Project.created_at.desc())
    ).all()
    return projects

# --------------------------------------------------------
#   Get Single Project (with organization check)
# --------------------------------------------------------
@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # ✅ Check if project belongs to user's organization
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    return project

# --------------------------------------------------------
#   Update Project (with organization check)
# --------------------------------------------------------
@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, 
    data: ProjectCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ✅ Check if project belongs to user's organization
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    project.name = data.name
    project.description = data.description
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

# --------------------------------------------------------
#   Delete Project (with organization check)
# --------------------------------------------------------
@router.delete("/{project_id}")
def delete_project(
    project_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ✅ Check if project belongs to user's organization
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    session.delete(project)
    session.commit()
    return {"message": "Project deleted successfully"}