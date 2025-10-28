# routes/invitation.py
import logging
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.database import get_session
from core.security import (
    create_access_token,
    hash_password,
    get_current_admin,
    get_current_user,
)
from models.models import Invitation, Organization, User, UserRole
from schemas.user_schema import AccountActivate, InvitationCreate
from services.email_service import email_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(tags=["Invitations"])

# Default frontend url (production) but allow override via env
DEFAULT_FRONTEND_URL = "https://teamflow-frontend.onrender.com"

# DEFAULT_FRONTEND_URL = "http://localhost:5173"
FRONTEND_URL = os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL)

INVITATION_VALID_DAYS = int(os.getenv("INVITATION_VALID_DAYS", "7"))  # used for DB expire field


# -----------------------
# Helper: build invite link
# -----------------------
def _build_invitation_link(token: str) -> str:
    """Build invitation link with UUID token"""
    return f"{FRONTEND_URL.rstrip('/')}/accept-invitation?token={token}"


# -----------------------
# Helper: get org name
# -----------------------
def _get_org_name(session: Session, org_id: int) -> str:
    try:
        org = session.exec(select(Organization).where(Organization.id == org_id)).first()
        return org.name if org and getattr(org, "name", None) else "Your Organization"
    except Exception:
        logger.exception("Failed to fetch organization name for id %s", org_id)
        return "Your Organization"


# ==================================================================
# Create / Send Invitation
# ==================================================================
@router.post("/invitations", response_model=dict)
async def invite(
    invite: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    """
    Create an invitation for a user within the current admin's organization.
    Uses UUID invitation token for the link and stores an Invitation record for audit.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="Unable to send invitation. The current user is not associated with any organization.")
    if not current_user.id:
        raise HTTPException(status_code=400, detail="Unable to identify the current user. Please log in again.")

    # check if user already exists in the same org
    existing = session.exec(
        select(User).where(User.email == invite.email, User.organization_id == org_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists in your organization.")

    # check for pending invitation in the same org
    pending = session.exec(
        select(Invitation).where(
            Invitation.email == invite.email,
            Invitation.organization_id == org_id,
            Invitation.accepted == False,
            Invitation.expires_at > datetime.utcnow(),
        )
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="An active invitation already exists for this email in your organization.")

    # Generate UUID token for invitation
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=INVITATION_VALID_DAYS)
    org_name = _get_org_name(session, org_id)
    invitation_link = _build_invitation_link(token)

    # attempt to send email (await)
    try:
        email_ok = await email_service.send_invitation_email(
            to_email=invite.email,
            invitation_link=invitation_link,
            role=invite.role,
            org_name=org_name,
            invited_by=(current_user.full_name or current_user.email),
        )
    except Exception as exc:
        logger.exception("Exception while calling email_service.send_invitation_email: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to send the invitation email. Please try again later.")

    if not email_ok:
        logger.error("Email service reported failure sending to %s", invite.email)
        raise HTTPException(status_code=500, detail="Unable to send the invitation email. Please check the email address or try again later.")

    # store invitation record for audit
    try:
        if not current_user.id:
            raise HTTPException(status_code=400, detail="Unable to identify the current user.")
        invitation = Invitation(
            email=invite.email,
            token=token,
            role=invite.role,
            expires_at=expires_at,
            sent_by_id=current_user.id,
            organization_id=org_id,
            accepted=False,
            created_at=datetime.utcnow(),
        )
        session.add(invitation)
        session.commit()
        session.refresh(invitation)
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        if "uq_org_invite_email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invitation for this email already exists in this organization."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A database constraint was violated while creating the invitation. Please try again."
            )
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("Failed to store invitation record for %s: %s", invite.email, e)
        raise HTTPException(status_code=500, detail="A database error occurred while saving the invitation.")
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to store invitation record for %s: %s", invite.email, exc)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while creating the invitation.")

    return {
        "message": "Invitation sent successfully.",
        "email": invite.email,
        "role": invite.role,
        "expires_at": invitation.expires_at.isoformat(),
        "invitation_link": invitation_link,
        "invitation_id": invitation.id,
    }


# ==================================================================
# Validate invitation token
# ==================================================================
@router.get("/invitations/validate/{token}", response_model=dict)
def validate_invitation(token: str, session: Session = Depends(get_session)):
    """Validate an invitation token."""
    invitation = session.exec(select(Invitation).where(Invitation.token == token)).first()
    
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation link.")
    if invitation.accepted:
        raise HTTPException(status_code=400, detail="This invitation has already been accepted.")
    if datetime.utcnow() > invitation.expires_at:
        raise HTTPException(status_code=400, detail="This invitation has expired. Please request a new one.")

    logger.info("Invitation token validated for %s (org %s)", invitation.email, invitation.organization_id)
    return {
        "valid": True,
        "email": invitation.email,
        "role": invitation.role,
        "organization_id": invitation.organization_id,
        "expires_at": invitation.expires_at.isoformat(),
    }


# ==================================================================
# Accept invitation - create account
# ==================================================================
@router.post("/invitations/accept", response_model=dict)
def accept_invite(data: AccountActivate, session: Session = Depends(get_session)):
    """Accept an invitation and activate the user account."""
    token = data.token
    if not token:
        raise HTTPException(status_code=400, detail="Invitation token is missing in the request.")

    invitation_record = session.exec(select(Invitation).where(Invitation.token == token)).first()
    if not invitation_record:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation link.")
    if invitation_record.accepted:
        raise HTTPException(status_code=400, detail="This invitation has already been accepted.")
    if datetime.utcnow() > (invitation_record.expires_at or datetime.min):
        raise HTTPException(status_code=400, detail="This invitation has expired. Please request a new one.")

    email = invitation_record.email
    org_id = invitation_record.organization_id
    role = invitation_record.role

    existing_user = session.exec(
        select(User).where(User.email == email, User.organization_id == org_id)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email already exists in your organization. Please log in instead.")

    # Create user
    try:
        user = User(
            full_name=data.full_name,
            email=email,
            password_hash=hash_password(data.password),
            role=role,
            organization_id=org_id,
            is_active=True,
            is_invited=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        if "uq_org_email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists in this organization."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A database constraint was violated while creating your account. Please try again."
            )
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("Failed to create user from invitation for %s: %s", email, e)
        raise HTTPException(status_code=500, detail="A database error occurred while creating your account.")
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to create user from invitation for %s: %s", email, exc)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while activating your account.")

    # Mark invitation record accepted if exists (audit)
    try:
        invitation_record.accepted = True
        invitation_record.accepted_at = datetime.utcnow()
        session.add(invitation_record)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception("Failed to mark invitation as accepted for %s: %s", email, e)
        # Not fatal for the user creation flow

    # Issue access token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "user_id": user.id,
            "organization_id": user.organization_id,
        }
    )
    print(f"DEBUG: Generated JWT payload: sub={user.email}, role={user.role}, user_id={user.id}, organization_id={user.organization_id}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": True,
            "is_invited": True,
            "organization_id": user.organization_id,
            "created_at": user.created_at.isoformat(),
        },
    }


# ==================================================================
# Get invitations for current user's organization
# ==================================================================
@router.get("/my-invitations", response_model=list[dict])
def get_my_invitations(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="You are not associated with any organization.")

    invitations = session.exec(
        select(Invitation).where(Invitation.organization_id == org_id)
    ).all()

    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "status": "accepted" if inv.accepted else "pending",
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "organization_id": inv.organization_id,
            "accepted": inv.accepted,
            "sent_by_id": inv.sent_by_id,
        }
        for inv in invitations
    ]


# ==================================================================
# Resend invitation
# ==================================================================
@router.post("/invitations/resend/{email}", response_model=dict)
async def resend_invitation(
    email: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="You are not associated with any organization.")

    invitation = session.exec(
        select(Invitation).where(
            Invitation.email == email,
            Invitation.organization_id == org_id,
            Invitation.accepted == False,
            Invitation.expires_at > datetime.utcnow(),
        )
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="No pending invitation found for this email in your organization.")

    # create new UUID token and update DB audit record
    new_token = str(uuid.uuid4())
    new_expires = datetime.utcnow() + timedelta(days=INVITATION_VALID_DAYS)
    invitation.token = new_token
    invitation.expires_at = new_expires
    invitation.created_at = datetime.utcnow()
    session.add(invitation)
    session.commit()
    session.refresh(invitation)

    invitation_link = _build_invitation_link(new_token)
    org_name = _get_org_name(session, org_id)

    try:
        email_ok = await email_service.send_invitation_email(
            to_email=email,
            invitation_link=invitation_link,
            role=invitation.role,
            org_name=org_name,
            invited_by=(current_user.full_name or current_user.email),
        )
    except Exception as exc:
        logger.exception("Failed to resend invitation email to %s: %s", email, exc)
        raise HTTPException(status_code=500, detail="Failed to resend the invitation email. Please try again later.")

    if not email_ok:
        raise HTTPException(status_code=500, detail="Email service reported failure while resending the invitation.")

    return {
        "message": "Invitation resent successfully.",
        "email": email,
        "role": invitation.role,
        "expires_at": invitation.expires_at.isoformat(),
        "invitation_link": invitation_link,
    }


# ==================================================================
# Revoke invitation
# ==================================================================
@router.delete("/invitations/{invitation_id}", response_model=dict)
def revoke_invitation(
    invitation_id: int, current_user: User = Depends(get_current_admin), session: Session = Depends(get_session)
):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="You are not associated with any organization.")

    invitation = session.exec(
        select(Invitation).where(Invitation.id == invitation_id, Invitation.organization_id == org_id)
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found in your organization.")
    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Cannot revoke an invitation that has already been accepted.")

    session.delete(invitation)
    session.commit()
    return {"message": "Invitation revoked successfully."}


# ==================================================================
# Organization members
# ==================================================================
@router.get("/organization-members", response_model=list[dict])
def get_organization_members(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="You are not associated with any organization.")

    users = session.exec(select(User).where(User.organization_id == org_id, User.is_active == True)).all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "is_invited": u.is_invited,
            "organization_id": u.organization_id,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


# ==================================================================
# Remove member from organization
# ==================================================================
@router.delete("/members/{user_id}", status_code=200)
def remove_member_from_organization(
    user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to remove members from this organization.")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if current_user.role != UserRole.SUPER_ADMIN.value and user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot remove members from another organization.")

    user.organization_id = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"success": True, "message": "Member removed from organization successfully."}
