# routes/tasks.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
from typing import List, Optional
from sqlmodel import delete
from datetime import datetime, date
from core.database import get_session
from models.models import Task, Project, User, TaskMemberLink, UserRole, TaskComment, TaskWorkLog
from schemas.task_schema import TaskCreate, TaskUpdate, TaskOut, TaskPermissionUpdate, CommentCreate, CommentOut, WorkLogCreate, WorkLogOut
from core.security import get_current_user, get_current_admin, get_current_member

router = APIRouter(tags=["Tasks"])


# ============================================================================
#  Helper function to check if user is assigned to task
# ============================================================================
def _is_user_assigned_to_task(session: Session, user_id: int, task_id: int) -> bool:
    assignment = session.exec(
        select(TaskMemberLink).where(
            TaskMemberLink.task_id == task_id,
            TaskMemberLink.user_id == user_id
        )
    ).first()
    return assignment is not None


# ============================================================================
#  Create New Task with Organization
# ============================================================================
@router.post("/", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """
    Create a new task.
    Only admins can create tasks.
    """
    # Validate project exists and belongs to user's organization
    project = session.exec(
        select(Project).where(
            Project.id == payload.project_id,
            Project.organization_id == current_user.organization_id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not in your organization"
        )

    # Determine which members to assign
    member_ids_to_assign = []
    if payload.member_ids and len(payload.member_ids) > 0:
        member_ids_to_assign = payload.member_ids
    elif payload.member_id is not None:
        member_ids_to_assign = [payload.member_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either member_id or member_ids must be provided"
        )

    # Validate all members exist and belong to the same organization
    if member_ids_to_assign:
        members = session.exec(
            select(User).where(
                User.id.in_(member_ids_to_assign),
                User.organization_id == current_user.organization_id
            )
        ).all()
        
        if len(members) != len(member_ids_to_assign):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more members not found or not in your organization"
            )

    # Handle date conversion for due_date
    parsed_due_date = None
    if payload.due_date:
        if isinstance(payload.due_date, str):
            try:
                # Parse the 'YYYY-MM-DD' string into a Python date object
                parsed_due_date = date.fromisoformat(payload.due_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid date format for due_date '{payload.due_date}'. Expected YYYY-MM-DD."
                )
        elif isinstance(payload.due_date, (date, datetime)):
            # If it's already a date/datetime object
            parsed_due_date = payload.due_date if isinstance(payload.due_date, date) else payload.due_date.date()
        else:
            # Unexpected type for due_date
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid type for due_date: {type(payload.due_date)}"
            )

    # Create the task
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=parsed_due_date,
        project_id=payload.project_id,
        organization_id=current_user.organization_id,
        allow_member_edit=payload.allow_member_edit
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    # Assign members to the task
    if member_ids_to_assign:
        for member_id in member_ids_to_assign:
            link = TaskMemberLink(task_id=task.id, user_id=member_id)
            session.add(link)
        session.commit()

    # Refresh task to get the relationships
    session.refresh(task)
    
    # Get project name for response
    project_name = project.name
    
    # Get member names for response
    member_names = [member.full_name for member in members] if members else []
    
    # Return enhanced task object
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        organization_id=task.organization_id,
        allow_member_edit=task.allow_member_edit,
        created_at=task.created_at,
        member_ids=member_ids_to_assign,
        project_name=project_name,
        member_names=member_names
    )


# ============================================================================
#  Get All Tasks (Organization-scoped)
# ============================================================================
@router.get("/", response_model=List[TaskOut])
def get_tasks(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get all tasks for the user's organization.
    Admins see all tasks, members see only their assigned tasks.
    """
    if organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tasks from your own organization"
        )

    if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        # Admins see all tasks in the organization
        tasks = session.exec(
            select(Task).where(Task.organization_id == organization_id)
        ).all()
    else:
        # Members see only their assigned tasks
        tasks = session.exec(
            select(Task)
            .join(TaskMemberLink)
            .where(
                Task.organization_id == organization_id,
                TaskMemberLink.user_id == current_user.id
            )
        ).all()

    # Enhance tasks with project and member information
    enhanced_tasks = []
    for task in tasks:
        # Get project name
        project = session.get(Project, task.project_id)
        project_name = project.name if project else None
        
        # Get member IDs and names
        member_links = session.exec(
            select(TaskMemberLink).where(TaskMemberLink.task_id == task.id)
        ).all()
        member_ids = [link.user_id for link in member_links]
        
        member_names = []
        if member_ids:
            members = session.exec(
                select(User).where(User.id.in_(member_ids))
            ).all()
            member_names = [member.full_name for member in members]

        enhanced_task = TaskOut(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            project_id=task.project_id,
            organization_id=task.organization_id,
            allow_member_edit=task.allow_member_edit,
            created_at=task.created_at,
            member_ids=member_ids,
            project_name=project_name,
            member_names=member_names
        )
        enhanced_tasks.append(enhanced_task)

    return enhanced_tasks


# ============================================================================
#  Get Single Task
# ============================================================================
@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get a single task by ID.
    Admins can view any task in their organization.
    Members can only view tasks assigned to them.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check organization access
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    # For members, check if they're assigned to the task
    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this task"
            )

    # Get project name
    project = session.get(Project, task.project_id)
    project_name = project.name if project else None
    
    # Get member IDs and names
    member_links = session.exec(
        select(TaskMemberLink).where(TaskMemberLink.task_id == task.id)
    ).all()
    member_ids = [link.user_id for link in member_links]
    
    member_names = []
    if member_ids:
        members = session.exec(
            select(User).where(User.id.in_(member_ids))
        ).all()
        member_names = [member.full_name for member in members]

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        organization_id=task.organization_id,
        allow_member_edit=task.allow_member_edit,
        created_at=task.created_at,
        member_ids=member_ids,
        project_name=project_name,
        member_names=member_names
    )



# ============================================================================
#   Update Task
# ============================================================================

@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update a task.
    Members can only update their own tasks' status.
    Admins can update any task in their organization.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    #  Check if task belongs to user's organization
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )
    
    # For members, restrict what they can update
    is_admin_user = current_user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
    if not is_admin_user:
        # Check if member is assigned to this task
        has_access = session.exec(
            select(TaskMemberLink).where(
                TaskMemberLink.task_id == task_id,
                TaskMemberLink.user_id == current_user.id
            )
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own tasks"
            )
        
        # Allow only status update for members
        allowed_fields = {'status'}
        provided_fields = set(payload.dict(exclude_unset=True).keys())
        if not provided_fields.issubset(allowed_fields):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Members can only update task status"
            )
    
    # Handle member assignment updates (only admins can do this)
    if (payload.member_ids is not None or payload.member_id is not None) and not is_admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update task assignments"
        )
    
    if payload.member_ids is not None or payload.member_id is not None:
        # Clear existing assignments
        existing_links = session.exec(
            select(TaskMemberLink).where(TaskMemberLink.task_id == task_id)
        ).all()
        for link in existing_links:
            session.delete(link)
        
        # Determine new member assignments
        member_ids_to_assign = []
        if payload.member_ids is not None:
            member_ids_to_assign = payload.member_ids
        elif payload.member_id is not None:
            member_ids_to_assign = [payload.member_id]
        
        # Validate and create new assignments
        if member_ids_to_assign:
            members = session.exec(
                select(User).where(
                    User.id.in_(member_ids_to_assign),
                    User.organization_id == current_user.organization_id
                )
            ).all()
            
            if len(members) != len(member_ids_to_assign):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more members not found or not in your organization"
                )
            
            for member_id in member_ids_to_assign:
                link = TaskMemberLink(task_id=task_id, user_id=member_id)
                session.add(link)
    
    # Update other fields
    update_data = payload.dict(exclude_unset=True, exclude={'member_id', 'member_ids'})
    for key, value in update_data.items():
        setattr(task, key, value)
    
    session.add(task)
    session.commit()
    session.refresh(task)
    
    # Prepare response with member information
    member_ids = session.exec(
        select(TaskMemberLink.user_id).where(TaskMemberLink.task_id == task.id)
    ).all()
    
    task_out = TaskOut.model_validate(task)
    task_out.member_ids = member_ids
    return task_out



# ============================================================================
#   Delete Task
# ============================================================================
@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """
    Delete a task.
    Only admins can delete tasks.
    This will also remove related TaskComment, TaskWorkLog and TaskMemberLink rows
    to avoid FK/NOT NULL integrity errors.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check organization access
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    try:
        # Delete related comments
        session.exec(delete(TaskComment).where(TaskComment.task_id == task.id))

        # Delete related work logs
        session.exec(delete(TaskWorkLog).where(TaskWorkLog.task_id == task.id))

        # Delete task-member links
        session.exec(delete(TaskMemberLink).where(TaskMemberLink.task_id == task.id))

        # Finally delete the task itself
        session.delete(task)
        session.commit()
    except Exception as e:
        # Rollback in case something went wrong and return 500 with message
        session.rollback()
        # Log the original exception to the server console (use your logger if any)
        print("Error deleting task:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task. See server logs for details."
        )


# ============================================================================
#  Member: Update task status only
# ============================================================================
@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Allow members to update only the status of their assigned tasks.
    Admins can use this too.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check organization
    if task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="You don't have access to this task")

    # Check role
    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(status_code=403, detail="You are not assigned to this task")

    # Only update status
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing status field")

    task.status = new_status
    session.commit()
    session.refresh(task)

    # Get project name
    project = session.get(Project, task.project_id)
    project_name = project.name if project else None

    # Get members
    member_links = session.exec(
        select(TaskMemberLink).where(TaskMemberLink.task_id == task.id)
    ).all()
    member_ids = [link.user_id for link in member_links]
    members = session.exec(select(User).where(User.id.in_(member_ids))).all()
    member_names = [m.full_name for m in members]

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        organization_id=task.organization_id,
        allow_member_edit=task.allow_member_edit,
        created_at=task.created_at,
        member_ids=member_ids,
        project_name=project_name,
        member_names=member_names
    )


# ============================================================================
#  Task Comments
# ============================================================================
@router.get("/{task_id}/comments", response_model=List[CommentOut])
def get_task_comments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get all comments for a task.
    Users can only view comments for tasks they have access to.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check access permissions
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this task"
            )

    comments = session.exec(
        select(TaskComment)
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.desc())
    ).all()

    # Enhance comments with user names
    enhanced_comments = []
    for comment in comments:
        user = session.get(User, comment.user_id)
        user_name = user.full_name if user else "Unknown User"
        
        enhanced_comment = CommentOut(
            id=comment.id,
            task_id=comment.task_id,
            user_id=comment.user_id,
            message=comment.message,
            created_at=comment.created_at,
            user_name=user_name
        )
        enhanced_comments.append(enhanced_comment)

    return enhanced_comments


# --------------------------------------------------------
#   CREATE TASK COMMENTS
# --------------------------------------------------------
@router.post("/{task_id}/comments", response_model=CommentOut, status_code=201)
def create_task_comment(
    task_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Add a comment to a task.
    Users can comment on tasks they have access to.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check access permissions
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this task"
            )

    comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        message=payload.message
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)

    return CommentOut(
        id=comment.id,
        task_id=comment.task_id,
        user_id=comment.user_id,
        message=comment.message,
        created_at=comment.created_at,
        user_name=current_user.full_name
    )


# ============================================================================
#  Task Work Logs
# ============================================================================

@router.get("/{task_id}/worklogs", response_model=List[WorkLogOut])
def get_task_work_logs(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get all work logs for a task.
    Users can only view work logs for tasks they have access to.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check access permissions
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this task"
            )

    work_logs = session.exec(
        select(TaskWorkLog)
        .where(TaskWorkLog.task_id == task_id)
        .order_by(TaskWorkLog.date.desc())
    ).all()

    # Enhance work logs with user names
    enhanced_work_logs = []
    for work_log in work_logs:
        user = session.get(User, work_log.user_id)
        user_name = user.full_name if user else "Unknown User"
        
        enhanced_work_log = WorkLogOut(
            id=work_log.id,
            task_id=work_log.task_id,
            user_id=work_log.user_id,
            hours=work_log.hours,
            date=work_log.date,
            description=work_log.description,
            created_at=work_log.created_at,
            user_name=user_name
        )
        enhanced_work_logs.append(enhanced_work_log)

    return enhanced_work_logs


# --------------------------------------------------------
#   CREATE Task Work Logs
# --------------------------------------------------------
@router.post("/{task_id}/worklogs", response_model=WorkLogOut, status_code=201)
def create_task_work_log(
    task_id: int,
    payload: WorkLogCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Add a work log to a task.
    Users can log work on tasks they have access to.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check access permissions
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    if current_user.role == UserRole.MEMBER:
        if not _is_user_assigned_to_task(session, current_user.id, task_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this task"
            )

    # Handle date
    log_date = payload.date or datetime.utcnow()

    work_log = TaskWorkLog(
        task_id=task_id,
        user_id=current_user.id,
        hours=payload.hours,
        description=payload.description,
        date=log_date
    )
    session.add(work_log)
    session.commit()
    session.refresh(work_log)

    return WorkLogOut(
        id=work_log.id,
        task_id=work_log.task_id,
        user_id=work_log.user_id,
        hours=work_log.hours,
        date=work_log.date,
        description=work_log.description,
        created_at=work_log.created_at,
        user_name=current_user.full_name
    )



# ============================================================================
#   Toggle Task Permission
# ============================================================================
@router.patch("/{task_id}/permission", response_model=TaskOut)
def toggle_task_permission(
    task_id: int,
    payload: TaskPermissionUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """
    Toggle member edit permission for a task.
    Only admins can change task permissions.
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check organization access
    if task.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    task.allow_member_edit = payload.allow_member_edit
    session.commit()
    session.refresh(task)

    # Get project name
    project = session.get(Project, task.project_id)
    project_name = project.name if project else None
    
    # Get member IDs and names
    member_links = session.exec(
        select(TaskMemberLink).where(TaskMemberLink.task_id == task.id)
    ).all()
    member_ids = [link.user_id for link in member_links]
    
    member_names = []
    if member_ids:
        members = session.exec(
            select(User).where(User.id.in_(member_ids))
        ).all()
        member_names = [member.full_name for member in members]

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        organization_id=task.organization_id,
        allow_member_edit=task.allow_member_edit,
        created_at=task.created_at,
        member_ids=member_ids,
        project_name=project_name,
        member_names=member_names
    )



# --------------------------------------------------------
#   Update Task Status (Member Safe) status-only patch (admins + assigned members)
# --------------------------------------------------------
@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    payload: dict,                       # { "status": "In Progress" }
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # organization check
    if task.organization_id != current_user.organization_id:
        raise HTTPException(403, "No access to this task")

    # members must be assigned
    if current_user.role == UserRole.MEMBER:
        assigned = session.exec(
            select(TaskMemberLink).where(
                TaskMemberLink.task_id == task_id,
                TaskMemberLink.user_id == current_user.id
            )
        ).first()
        if not assigned:
            raise HTTPException(403, "You are not assigned to this task")

    # update only the status column
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(400, "status field required")

    task.status = new_status
    session.commit()
    session.refresh(task)

    # build the same response shape the frontend expects
    member_links = session.exec(
        select(TaskMemberLink).where(TaskMemberLink.task_id == task.id)
    ).all()
    member_ids = [link.user_id for link in member_links]
    members = session.exec(select(User).where(User.id.in_(member_ids))).all()
    project = session.get(Project, task.project_id)

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        organization_id=task.organization_id,
        allow_member_edit=task.allow_member_edit,
        created_at=task.created_at,
        member_ids=member_ids,
        project_name=project.name if project else None,
        member_names=[m.full_name for m in members],
    )

