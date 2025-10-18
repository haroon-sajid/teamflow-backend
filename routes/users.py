
# routes/users.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
from typing import List

from models.models import User, UserRole
from schemas.user_schema import UserCreate, UserRead, UserUpdate
from core.database import get_session
from core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])


# ----------------------------------------------------------------------
# ✅ Get Current User
# ----------------------------------------------------------------------
@router.get("/me", response_model=UserRead)
def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    """Return current user info (decoded from JWT)."""
    return current_user


# ----------------------------------------------------------------------
# ✅ Update Current User Profile (Self)
# ----------------------------------------------------------------------
@router.put("/me", response_model=UserRead)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Allow a user to update their own profile (within org scope)."""

    # Scoped email uniqueness check
    if user_update.email and user_update.email != current_user.email:
        existing_user = session.exec(
            select(User).where(
                User.email == user_update.email,
                User.organization_id == current_user.organization_id
            )
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered in this organization."
            )
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    # Only admins/super admins can modify role or active status
    if user_update.role is not None:
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change user roles."
            )
        current_user.role = user_update.role

    if user_update.is_active is not None:
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change active status."
            )
        current_user.is_active = user_update.is_active

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


# ----------------------------------------------------------------------
# ✅ Get All Users (Organization-Scoped, Admin only)
# ----------------------------------------------------------------------
@router.get("/", response_model=List[UserRead])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Admins: list all users in your organization."""
    users = session.exec(
        select(User).where(User.organization_id == current_user.organization_id)
    ).all()
    return users


# ----------------------------------------------------------------------
# ✅ Get User by ID (Org-Scoped)
# ----------------------------------------------------------------------
@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Retrieve a user by ID (must be in the same organization)."""
    user = session.exec(
        select(User)
        .where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Members can only see their own profile
    if current_user.role == UserRole.MEMBER.value and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile."
        )
    return user


# ----------------------------------------------------------------------
# ✅ Update Another User (Admin only)
# ----------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Admin: update a user within your organization."""
    user = session.exec(
        select(User)
        .where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Scoped email uniqueness
    if user_update.email and user_update.email != user.email:
        existing_user = session.exec(
            select(User).where(
                User.email == user_update.email,
                User.organization_id == current_user.organization_id
            )
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered in this organization."
            )
        user.email = user_update.email

    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ----------------------------------------------------------------------
# ✅ Delete User (Admin only)
# ----------------------------------------------------------------------
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Admin: delete a user within your organization."""
    user = session.exec(
        select(User)
        .where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    session.delete(user)
    session.commit()
    return {"message": "User deleted successfully."}


# ----------------------------------------------------------------------
# ✅ Get All Members of Organization
# ----------------------------------------------------------------------
@router.get("/organization/members", response_model=List[UserRead])
def get_organization_members(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Return all active users in the same organization."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to any organization."
        )

    members = session.exec(
        select(User)
        .where(
            User.organization_id == current_user.organization_id,
            User.is_active == True
        )
    ).all()
    return members
