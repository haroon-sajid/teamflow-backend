
# core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from core.database import get_session
from models.models import User, UserRole
import secrets

# ========================================
# 🔑 SECRET KEY & JWT SETTINGS
# ========================================
SECRET_KEY = "your_super_secret_key_please_change_this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ========================================
# 🔐 Password Hashing
# ========================================
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def hash_password(password: str) -> str:
#     """Hash a plain password for storing in the database."""
#     if len(password) > 72:
#         password = password[:72]  # bcrypt max length
#     return pwd_context.hash(password)

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Verify a plain password against the hashed one."""
#     if len(plain_password) > 72:
#         plain_password = plain_password[:72]
#     return pwd_context.verify(plain_password, hashed_password)



import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # Step 1: normalize any-length password using SHA256
    password_bytes = password.encode("utf-8")
    sha256_digest = hashlib.sha256(password_bytes).hexdigest()

    # Step 2: bcrypt hash the digest
    return pwd_context.hash(sha256_digest)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(plain_digest, hashed_password)


# ========================================
# 🔑 JWT Token Generation & Verification
# ========================================
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT token with optional expiration time."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ========================================
# 🔐 OAuth2 Security Dependency
# ========================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ========================================
# 👤 Get Current User (Returns full User object from DB)
# ========================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """Extract user info from JWT and fetch full User from DB."""
    payload = decode_access_token(token)
    email: str = payload.get("sub")
    role: str = payload.get("role")
    user_id: int = payload.get("user_id")
    organization_id: int = payload.get("organization_id")  # ✅ Added organization support

    if not email or not role or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")
    
    # ✅ Verify user belongs to the organization in the token
    if organization_id and user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized for this organization.")

    return user

# ========================================
# 🛡️ Role-Based Access Control (RBAC) - UPDATED
# ========================================
def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Only Super Admin can access this."""
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin or Super Admin can access this."""
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def get_current_member(current_user: User = Depends(get_current_user)) -> User:
    """Members, Admins, and Super Admins can access this."""
    if current_user.role not in [UserRole.MEMBER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def get_current_user_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow user to access their own data or admin to access any data."""
    return current_user

# ========================================
# 🔑 Invitation Token Generation
# ========================================
def generate_invitation_token() -> str:
    """Generate secure random token for invitations."""
    return secrets.token_urlsafe(32)