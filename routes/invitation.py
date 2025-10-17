# routes/invitation.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from sqlmodel import Session, select
from datetime import datetime, timedelta
import secrets
import os
from core.database import get_session
from services.email_service import email_service 
from models.models import User, Invitation, UserRole, Organization
from schemas.user_schema import InvitationCreate, AccountActivate, UserRead, UserCreate
from core.security import (hash_password, create_access_token, get_current_admin, get_current_user)

router = APIRouter(tags=["Invitations"])


# ==================================================================
# ✅ SEND INVITE EMAIL
# ================================================================== 
async def send_invite_email_sync(email_to: str, token: str, role: str, invited_by: str = "Admin"):
    """Send beautiful HTML invitation email using our custom email service"""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    # ⚠️ token from secrets.token_urlsafe() is ALREADY URL-safe — no need to quote!
    invitation_link = f"{frontend_url}/accept-invitation?token={token}"
    
    
    try:
        success = await email_service.send_invitation_email(
            to_email=email_to,
            invitation_link=invitation_link,
            role=role,
            invited_by=invited_by
        )
        return success
    except Exception as e:
        print(f" Error sending email: {e}")
        return False


# ==================================================================
# ✅ CREATE INVITATION REQUEST 
# ================================================================== 
@router.post("/invitations", response_model=dict)
async def invite(
    invite: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    existing = session.exec(select(User).where(User.email == invite.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    existing_invite = session.exec(
        select(Invitation).where(
            Invitation.email == invite.email,
            Invitation.accepted == False,
            Invitation.expires_at > datetime.utcnow()
        )
    ).first()
    
    if existing_invite:
        raise HTTPException(status_code=400, detail="Pending invitation already exists for this email.")

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(days=7)

    # Send email first
    email_sent = await send_invite_email_sync(
        invite.email, 
        token, 
        invite.role,
        current_user.full_name or current_user.email
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send invitation email.")

    invitation = Invitation(
        email=invite.email,
        token=token,
        role=invite.role,
        expires_at=expires,
        sent_by_id=current_user.id,
        organization_id=current_user.organization_id,
        accepted=False,
        created_at=datetime.utcnow()
    )
    session.add(invitation)
    session.commit()
    session.refresh(invitation)

    # Return link — no quoting needed
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    invitation_link = f"{frontend_url}/accept-invitation?token={token}"

    return {
        "message": "Invitation sent successfully!",
        "email": invite.email,
        "role": invite.role,
        "expires_at": invitation.expires_at.isoformat(),
        "invitation_link": invitation_link
    }


# =====================================================================
# ✅ ACCEPT EMAIL INVITATION REQUEST
# =====================================================================
@router.post("/invitations/accept", response_model=dict) 
def accept_invite(
    data: AccountActivate,
    session: Session = Depends(get_session)
):
    """Accept an invitation and create user account."""
    inv = session.exec(select(Invitation).where(Invitation.token == data.token)).first()
    if not inv:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if inv.accepted:
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    if datetime.utcnow() > inv.expires_at:
        raise HTTPException(status_code=400, detail="Token expired")

    existing_user = session.exec(select(User).where(User.email == inv.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="User with this email already exists. Please login instead."
        )

    user = User(
        full_name=data.full_name,
        email=inv.email,
        password_hash=hash_password(data.password),
        role=inv.role,
        organization_id=inv.organization_id,
        is_active=True,
        is_invited=True,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    inv.accepted = True
    inv.accepted_at = datetime.utcnow()
    session.add(inv)
    session.commit()

    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role,
            "user_id": user.id,
            "organization_id": user.organization_id
        }
    )
    
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
            "created_at": user.created_at.isoformat()
        }
    }


# ==================================================================
# ✅ VALIDATE INVITATION TOKEN
# ================================================================== 
@router.get("/invitations/validate/{token}")
def validate_invitation(token: str, session: Session = Depends(get_session)):
    # ⚠️ NO unquote needed — token is passed as-is and is URL-safe
    invitation = session.exec(
        select(Invitation).where(Invitation.token == token)
    ).first()

    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid invitation token.")
    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Invitation already accepted.")
    if datetime.utcnow() > invitation.expires_at:
        raise HTTPException(status_code=400, detail="Invitation has expired.")

    return {
        "valid": True,
        "email": invitation.email,
        "role": invitation.role,
        "organization_id": invitation.organization_id,
        "expires_at": invitation.expires_at.isoformat()
    }


# ==================================================================
# ✅ GET MY INVITATIONS (for current user's organization)
# ================================================================== 
@router.get("/my-invitations", response_model=list[dict])
def get_my_invitations(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this organization's invitations")
    
    invitations = session.exec(
        select(Invitation).where(Invitation.organization_id == organization_id)
        .order_by(Invitation.created_at.desc())
    ).all()
    
    return [
        {
            "id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "status": "accepted" if invite.accepted else "pending",
            "created_at": invite.created_at.isoformat(),
            "expires_at": invite.expires_at.isoformat(),
            "organization_id": invite.organization_id,
            "accepted": invite.accepted,
            "sent_by_id": invite.sent_by_id
        }
        for invite in invitations
    ]


# ==================================================================
# ✅ GET ALL MEMBERS OF CURRENT ORGANIZATION
# ================================================================== 
@router.get("/organization-members", response_model=list[dict])
def get_organization_members(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    users = session.exec(
        select(User).where(User.organization_id == current_user.organization_id)
        .order_by(User.full_name, User.email)
    ).all()
    
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_invited": user.is_invited,
            "organization_id": user.organization_id,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]


# ==================================================================
# ✅ RESEND EMAIL INVITATION REQUEST
# ================================================================== 
@router.post("/invitations/resend/{email}", response_model=dict)
async def resend_invitation(
    email: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    invitation = session.exec(
        select(Invitation).where(
            Invitation.email == email,
            Invitation.sent_by_id == current_user.id,
            Invitation.accepted == False,
            Invitation.expires_at > datetime.utcnow()
        )
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="No pending invitation found for this email.")

    new_token = secrets.token_urlsafe(32)
    new_expires = datetime.utcnow() + timedelta(days=7)

    email_sent = await send_invite_email_sync(
        email, 
        new_token, 
        invitation.role,
        current_user.full_name or current_user.email
    )
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to resend invitation email.")

    invitation.token = new_token
    invitation.expires_at = new_expires
    invitation.created_at = datetime.utcnow()
    session.add(invitation)
    session.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    invitation_link = f"{frontend_url}/accept-invitation?token={new_token}"

    return {
        "message": "Invitation resent successfully!",
        "email": email,
        "role": invitation.role,
        "expires_at": new_expires.isoformat(),
        "invitation_link": invitation_link
    }


# ==================================================================
# ✅ REVOKE EMAIL INVITATION REQUEST 
# ================================================================== 
@router.delete("/invitations/{invitation_id}", response_model=dict)
def revoke_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    invitation = session.get(Invitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if invitation.sent_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this invitation.")

    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Cannot revoke an invitation that has already been accepted.")

    session.delete(invitation)
    session.commit()

    return {
        "message": "Invitation revoked successfully!"
    }


# ==================================================================
# ✅ REMOVE MEMBER FROM ORGANIZATION
# ==================================================================
@router.delete("/members/{user_id}", status_code=200)
def remove_member_from_organization(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role != UserRole.SUPER_ADMIN.value:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this user")

    user.organization_id = None
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"success": True, "message": "Member removed from organization"}