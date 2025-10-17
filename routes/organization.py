# routes/organization.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from core.database import get_session
from core.security import get_current_user, get_current_admin
from models.models import User, Organization
from schemas.organization_schema import OrganizationRead, OrganizationCreate, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ==================================================================
#  ✅ GET MY ORGANIZATION
# ================================================================== 
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

# ==================================================================
#  ✅ UPDATE MY ORGANIZATION
# ================================================================== 
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

# ==================================================================
#  ✅ GET ALL ORGANIZATION
# ================================================================== 
@router.get("/", response_model=List[OrganizationRead])
def get_all_organizations(
    current_user: User = Depends(get_current_admin),  # Only admins can see all orgs
    session: Session = Depends(get_session)
):
    """Get all organizations (admin only)"""
    organizations = session.exec(select(Organization)).all()
    return organizations

# ==================================================================
#  ✅ GET ORGANIZATION
# ================================================================== 
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