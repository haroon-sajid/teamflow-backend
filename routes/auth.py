from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlmodel import Session, select
from datetime import datetime
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.models import User, UserRole, Organization
from schemas.user_schema import UserLogin, UserCreate, UserRead
from core.database import get_session
from core.security import (
    hash_password, verify_password, create_access_token,
    get_current_user
)

router = APIRouter(tags=["Authentication"])


# ==========================================================
# ✅ Generate a clean slug
# ==========================================================
def generate_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


# ==========================================================
# ✅ Public Signup (creates org + admin)
# ==========================================================
@router.post("/signup")
def public_signup(user_data: UserCreate, session: Session = Depends(get_session)):
    """Public signup – creates new organization and admin user"""
    try:
        print(f"📝 Signup attempt for {user_data.email}")

        org_name = f"{user_data.full_name}'s Organization"
        org_slug = generate_slug(org_name)

        organization = Organization(name=org_name, slug=org_slug)
        session.add(organization)
        session.commit()
        session.refresh(organization)

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

        access_token = create_access_token(
            data={
                "sub": new_user.email,
                "role": new_user.role,
                "user_id": new_user.id,
                "organization_id": new_user.organization_id,
            }
        )
        print(f"DEBUG: JWT payload: sub={new_user.email}, role={new_user.role}, org={new_user.organization_id}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "full_name": new_user.full_name,
                "email": new_user.email,
                "role": new_user.role,
                "is_active": new_user.is_active,
                "organization_id": new_user.organization_id,
                "created_at": new_user.created_at.isoformat(),
            },
        }

    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        if "uq_org_email" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists. Please log in instead."
            )
        elif "uq_org_invite_email" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="An invitation has already been sent to this email."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="We couldn’t complete your signup. Please try again."
            )

    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Signup database error:", e)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while creating your account. Please try again later."
        )

    except Exception as e:
        session.rollback()
        print("❌ Unexpected signup error:", e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


# ==========================================================
# ✅ Login (multi-tenant aware)
# ==========================================================
@router.post("/login")
def login(
    user: UserLogin,
    organization_slug: str = Query(None, description="Organization slug (optional)"),
    session: Session = Depends(get_session),
):
    """Login for a specific organization using org slug or auto-detect"""
    try:
        if not organization_slug:
            db_user = session.exec(select(User).where(User.email == user.email)).first()
            if not db_user:
                raise HTTPException(status_code=404, detail="No account found with this email.")
            org_id = db_user.organization_id
        else:
            org = session.exec(select(Organization).where(Organization.slug == organization_slug)).first()
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found.")
            org_id = org.id

        db_user = session.exec(
            select(User).where(
                User.email == user.email,
                User.organization_id == org_id,
            )
        ).first()

        if not db_user:
            raise HTTPException(
                status_code=404,
                detail="No account found under this organization."
            )

        if not verify_password(user.password, db_user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password."
            )

        if not db_user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Your account is inactive. Please contact your admin."
            )

        token = create_access_token(
            data={
                "sub": db_user.email,
                "role": db_user.role,
                "user_id": db_user.id,
                "organization_id": db_user.organization_id,
            }
        )
        print(f"DEBUG: JWT payload: sub={db_user.email}, role={db_user.role}, org={db_user.organization_id}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "full_name": db_user.full_name,
                "email": db_user.email,
                "role": db_user.role,
                "organization_id": db_user.organization_id,
            },
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        print("❌ Login database error:", e)
        raise HTTPException(
            status_code=500,
            detail="We’re having trouble logging you in. Please try again later."
        )
    except Exception as e:
        print("❌ Unexpected login error:", e)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while logging in. Please try again."
        )


# ==========================================================
# ✅ Get current user from token
# ==========================================================
@router.get("/me", response_model=UserRead)
def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's info"""
    return current_user
