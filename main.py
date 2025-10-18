import os
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from core.database import create_db_and_tables, get_session
from core.security import get_current_user, get_current_admin
from models.models import User, UserRole

from routes.auth import router as auth_router
from routes.projects import router as project_router
from routes.tasks import router as tasks_router  
from routes.invitation import router as invitation_router

# =========================================
# 🧩 Users Router
# =========================================
users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("/", response_model=list[User])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Get all users in the same organization (admin only)."""
    users = session.exec(
        select(User).where(User.organization_id == current_user.organization_id)
    ).all()
    return users

@users_router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific user within your organization."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Unauthorized for this organization")

    if current_user.role == UserRole.MEMBER and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")

    return user


# =========================================
# 🏁 Lifespan
# =========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    print("✅ Database tables created on startup.")
    yield
    print("✅ Application shutting down.")


# =========================================
#  ✅ FastAPI App
# =========================================
app = FastAPI(lifespan=lifespan, title="TeamFlow App Backend")

allowed_origins = [
    "https://teamflow-frontend-omega.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================
# 📦 Routers
# =========================================
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(project_router, prefix="/projects", tags=["Projects"])
app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
app.include_router(users_router, tags=["Users"])
app.include_router(invitation_router, prefix="/auth", tags=["Invitations"])

# =========================================
# 🩺 Health Check
# =========================================
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/")
def read_root():
    return {"message": "Welcome to TeamFlow Backend!"}
