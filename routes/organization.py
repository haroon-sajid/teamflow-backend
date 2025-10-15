# routes/organization.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from core.database import get_session
from core.security import get_current_user, get_current_admin
from models.models import User, Organization
from schemas.organization_schema import OrganizationRead, OrganizationCreate, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# -------------------------------------------------------------------------------------
#  ✅ GET MY ORGANIZATION
# -------------------------------------------------------------------------------------
@router.get("/my-organization", response_model=OrganizationRead)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get current user's organization"""
    organization = session.get(Organization, current_user.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization

# -------------------------------------------------------------------------------------
#  ✅ UPDATE MY ORGANIZATION
# -------------------------------------------------------------------------------------
@router.put("/my-organization", response_model=OrganizationRead)
def update_my_organization(
    organization_update: OrganizationUpdate,
    current_user: User = Depends(get_current_admin),  # Only admins can update org
    session: Session = Depends(get_session)
):
    """Update current user's organization"""
    organization = session.get(Organization, current_user.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Update organization fields
    if organization_update.name is not None:
        organization.name = organization_update.name
    if organization_update.slug is not None:
        organization.slug = organization_update.slug
    
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization

# -------------------------------------------------------------------------------------
#  ✅ GET ALL ORGANIZATION
# -------------------------------------------------------------------------------------
@router.get("/", response_model=List[OrganizationRead])
def get_all_organizations(
    current_user: User = Depends(get_current_admin),  # Only admins can see all orgs
    session: Session = Depends(get_session)
):
    """Get all organizations (admin only)"""
    organizations = session.exec(select(Organization)).all()
    return organizations

# -------------------------------------------------------------------------------------
#  ✅ GET ORGANIZATION
# -------------------------------------------------------------------------------------
@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_admin),  # Only admins can see specific orgs
    session: Session = Depends(get_session)
):
    """Get a specific organization (admin only)"""
    organization = session.get(Organization, organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization






# ============================================================================
#   REMOVE MEMBER FROM ORGANIZATION
# ============================================================================

# routers/invitation.py (or routers/users.py) — add imports you already have
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from typing import List
from models.models import User  # import your User model
from schemas.user_schema import UserOut  # optional

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.delete("/members/{user_id}", status_code=200)
def remove_member_from_organization(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Remove a member from the current user's organization.
    Allowed: admins and super_admins.
    Action: set user's organization_id to None (or delete — we do set-to-None to be safe).
    """
    # Role check
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Organization isolation: admin can only remove within their organization
    if current_user.role != UserRole.SUPER_ADMIN.value:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this user")

    # Safe removal: remove organization link (do NOT delete personal user record)
    user.organization_id = None
    # optionally: user.is_active = False  # if you want to disable the account
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"success": True, "message": "Member removed from organization"}
