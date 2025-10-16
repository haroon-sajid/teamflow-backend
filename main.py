import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from core.database import create_db_and_tables, get_session
from routes.auth import router as auth_router
from routes.projects import router as project_router
from routes.tasks import router as tasks_router  
from routes.invitation import router as invitation_router

from fastapi import APIRouter, HTTPException, Depends
from core.security import get_current_user, get_current_admin
from models.models import User, UserRole

users_router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
#  ✅ GET ALL USERS
# ============================================================================

@users_router.get("/", response_model=list[User ])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session)
):
    """Get all users (admin only)"""
    users = session.exec(select(User)).all()
    return users

# ============================================================================
#  ✅ GET USERS
# ============================================================================
@users_router.get("/{user_id}", response_model=User )
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific user"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User  not found")

    if current_user.role == UserRole.MEMBER and current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only view your own profile"
        )
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    print("✅ Database tables created on startup.")
    yield
    print("✅ Application shutting down.")


# ============================================================================
#  ✅ CORSMiddleware Configuration
# ============================================================================

app = FastAPI(lifespan=lifespan, title="TeamFlow App Backend")

allowed_origins = [
    "http://localhost:5173",  # Your Vite dev server
    "http://127.0.0.1:5173",  # Alternative localhost format
    # Add other origins if needed, e.g., production URL
    # "https://yourproductiondomain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, #
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allows all headers
)

# ============================================================================
#  ✅ INCLUDE ROUTERS AFTER CORS
# ============================================================================
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(project_router, prefix="/projects", tags=["Projects"])
app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
app.include_router(users_router, tags=["Users"])
app.include_router(invitation_router, prefix="/auth", tags=["Invitations"])


# ============================================================================
#  ✅ HEALTH CHECK ROUTE
# ============================================================================
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}


@app.get("/")
def read_root():
    return {"message": "Welcome to TeamFlow Backend!"}
