import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from core.database import create_db_and_tables
from routes.auth import router as auth_router
from routes.projects import router as project_router
from routes.tasks import router as tasks_router
from routes.invitation import router as invitation_router
from routes.users import router as users_router      
from routes.profile import router as profile_router 
from routes.payment import router as payment_router
from routes.timesheet import router as timesheet_router




# =========================================
# 🏁 Lifespan (DB initialization)
# =========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    # If create_db_and_tables is async, use: await create_db_and_tables()
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
app.include_router(users_router, prefix="/users", tags=["Users"])       
app.include_router(invitation_router, prefix="/invitations", tags=["Invitations"])
app.include_router(profile_router, tags=["Profile"]) 
app.include_router(payment_router)  # ✅ Stripe Payment Integration
app.include_router(payment_router, prefix="/api/v1")
app.include_router(timesheet_router)



# Serve the entire uploads directory at /static
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# =========================================
# 🩺 Health Check
# =========================================
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}


@app.get("/")
def read_root():
    return {"message": "Welcome to TeamFlow Backend!"}

