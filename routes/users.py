#// routes/users.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlmodel import Session, select
from datetime import datetime, timedelta
import secrets
import os

from services.email_service import email_service
from typing import List, Optional
from models.models import User, UserRole, Invitation
from schemas.user_schema import UserCreate, UserRead, UserUpdate, InvitationCreate, AccountActivate
from core.database import get_session
from core.security import (hash_password, verify_password, create_access_token,generate_invitation_token, oauth2_scheme,
    get_current_user, get_current_admin, get_current_member)

router = APIRouter(tags=["Users"])

# --------------------------------------------------------
# ✅ GET CURRENT USER ENDPOINT
# --------------------------------------------------------
@router.get("/me", response_model=UserRead)
def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    """Get current user info from JWT token"""
    return current_user

# --------------------------------------------------------
# ✅ UPDATE CURRENT USER PROFILE
# --------------------------------------------------------
@router.put("/me", response_model=UserRead)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update current user's profile"""
    # Check if email is being updated and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = session.exec(select(User).where(User.email == user_update.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )
        current_user.email = user_update.email

    # Update other fields if provided
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.role is not None:
        # Only admins can change roles
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to change role."
            )
        current_user.role = user_update.role

    if user_update.is_active is not None:
        # Only admins can change active status
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

# --------------------------------------------------------
#  GET ALL USERS (ADMIN ONLY) - NOW ORGANIZATION-SPECIFIC
# --------------------------------------------------------
# @router.get("/", response_model=List[UserRead])
# def get_all_users(
#     current_user: User = Depends(get_current_admin),
#     session: Session = Depends(get_session)
# ):
#     """Get all users within the current admin's organization (admin only)"""
#     #  FIXED: Filter users by the current user's organization_id
#     users = session.exec(
#         select(User).where(User.organization_id == current_user.organization_id)
#     ).all()
#     return users


# --------------------------------------------------------
#  LIST USERS (org-scoped) – param taken from TOKEN
# --------------------------------------------------------
@router.get("/", response_model=List[UserRead])
def get_all_users(
    organisation_id: int | None = Query(None, include_in_schema=False),  # absorb what front-end sends
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Return only users that belong to the same organisation as the admin."""
    print(f"  token org: {current_user.organization_id}")   # debug – remove later
    users = session.exec(
        select(User).where(User.organization_id == current_user.organization_id)
    ).all()
    print(f"  returned: {[u.email for u in users]}")       # debug – remove later
    return users

# --------------------------------------------------------
#  GET USER BY ID
# --------------------------------------------------------
@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific user"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Members can only view their own profile
    if current_user.role == UserRole.MEMBER.value and current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only view your own profile"
        )
    
    return user

# --------------------------------------------------------
#  UPDATE USER (ADMIN ONLY)
# --------------------------------------------------------
@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Update a user (admin only)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if email is being updated and if it's already taken
    if user_update.email and user_update.email != user.email:
        existing_user = session.exec(select(User).where(User.email == user_update.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )
        user.email = user_update.email

    # Update other fields if provided
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

# --------------------------------------------------------
#  DELETE USER (ADMIN ONLY)
# --------------------------------------------------------
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Delete a user (admin only)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent users from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )

    session.delete(user)
    session.commit()

    return {"message": "User deleted successfully"}


# --------------------------------------------------------
#  GET ORGANIZATION MEMBER
# --------------------------------------------------------
router = APIRouter(prefix="/members", tags=["Members"])

@router.get("/organization", response_model=list[UserRead])
def get_organization_members(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    ✅ Return all accepted members (and admins) of the current user's organization.
    Only members from the same organization are shown.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to any organization"
        )

    members = session.exec(
        select(User)
        .where(
            User.organization_id == current_user.organization_id,
            User.is_active == True  # only active (accepted) members
        )
    ).all()

    return members


