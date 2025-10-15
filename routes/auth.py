# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional
import re

from models.models import User, UserRole, Invitation, Organization
from schemas.user_schema import UserLogin, InvitationCreate, AccountActivate, UserRead, UserCreate
from core.database import get_session
from core.security import (
    hash_password, verify_password, create_access_token,
    generate_invitation_token, get_current_admin, get_current_user
)

router = APIRouter(tags=["Authentication"])

def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from organization name"""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'\s+', '-', slug)  # Replace spaces with hyphens
    slug = re.sub(r'-+', '-', slug)  # Remove multiple hyphens
    slug = slug.strip('-')  # Remove leading/trailing hyphens
    return slug[:50]  # Limit to 50 characters

# --------------------------------------------------------
#  ✅ SIGNUP ROUTE WITH PROPER ERROR HANDLING
# --------------------------------------------------------
@router.post("/signup")
def public_signup(user_data: UserCreate, session: Session = Depends(get_session)):
    """Public signup - user becomes Admin and creates their organization"""
    try:
        print(f"📝 Signup attempt for: {user_data.email}")
        
        # Check if user already exists
        existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
        if existing_user:
            print(f" User already exists: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

        # Create organization name and slug
        org_name = f"{user_data.full_name}'s Organization"
        org_slug = generate_slug(org_name)
        
        print(f" Creating organization: {org_name} (slug: {org_slug})")
        
        # Create a new organization for this user
        organization = Organization(
            name=org_name,
            slug=org_slug,
            created_at=datetime.utcnow()
        )
        session.add(organization)
        session.commit()
        session.refresh(organization)
        
        print(f" Organization created with ID: {organization.id}")

        # Create user
        print(f"👤 Creating user: {user_data.full_name} ({user_data.email})")
        
        new_user = User(
            full_name=user_data.full_name,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=UserRole.ADMIN.value,
            organization_id=organization.id,
            is_active=True,
            is_invited=False,
            created_at=datetime.utcnow(),
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        print(f" User created with ID: {new_user.id}")
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": new_user.email,
                "role": new_user.role,
                "user_id": new_user.id,
                "organization_id": new_user.organization_id
            }
        )
        
        print(f" Token generated for user: {new_user.email}")
        
        # Return response
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "full_name": new_user.full_name,
                "email": new_user.email,
                "role": new_user.role,
                "is_active": new_user.is_active,
                "is_invited": new_user.is_invited,
                "organization_id": new_user.organization_id,
                "created_at": new_user.created_at.isoformat()
            }
        }
        
        print(f" Signup successful for: {new_user.email}")
        return response_data
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other errors and log them
        print(f" SIGNUP ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )


# --------------------------------------------------------
# ✅ LOGIN ROUTE
# --------------------------------------------------------
@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):
    try:
        print(f" Login attempt for: {user.email}")
        
        db_user = session.exec(select(User).where(User.email == user.email)).first()
        if not db_user:
            print(f" User not found: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email."
            )

        if not verify_password(user.password, db_user.password_hash):
            print(f" Invalid password for: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The password you entered is incorrect."
            )

        if not db_user.is_active:
            print(f" Inactive account: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Contact admin."
            )

        access_token = create_access_token(
            data={
                "sub": db_user.email,
                "role": db_user.role,
                "user_id": db_user.id,
                "organization_id": db_user.organization_id
            }
        )
        
        print(f" Login successful for: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "full_name": db_user.full_name or db_user.email.split("@")[0],
                "email": db_user.email,
                "role": db_user.role,
                "is_active": db_user.is_active,
                "is_invited": db_user.is_invited,
                "organization_id": db_user.organization_id,
                "created_at": db_user.created_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f" LOGIN ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

# --------------------------------------------------------
# ✅ GET CURRENT USER ENDPOINT
# --------------------------------------------------------
@router.get("/me", response_model=UserRead)
def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    """Get current user info from JWT token"""
    return current_user

