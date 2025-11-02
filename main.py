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




# =========================================
# 🏁 Lifespan (DB initialization)
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
app.include_router(users_router, prefix="/users", tags=["Users"])       
app.include_router(invitation_router, prefix="/auth", tags=["Invitations"])
app.include_router(profile_router, tags=["Profile"]) 
app.include_router(payment_router)  # ✅ Stripe Payment Integration
app.include_router(payment_router, prefix="/api/v1")

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





















# import os
# from dotenv import load_dotenv
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
# from fastapi.staticfiles import StaticFiles

# from core.database import create_db_and_tables
# from routes.auth import router as auth_router
# from routes.projects import router as project_router
# from routes.tasks import router as tasks_router
# from routes.invitation import router as invitation_router
# from routes.users import router as users_router      
# from routes.profile import router as profile_router 
# from routes.payment import router as payment_router

# # Load environment variables
# load_dotenv()

# # =========================================
# # 🏁 Lifespan (DB initialization)
# # =========================================
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     create_db_and_tables()
#     print("✅ Database tables created on startup.")
#     yield
#     print("✅ Application shutting down.")


# # =========================================
# #  ✅ FastAPI App
# # =========================================
# app = FastAPI(
#     lifespan=lifespan, 
#     title="TeamFlow App Backend",
#     description="TeamFlow Project Management API",
#     version="1.0.0"
# )

# # =========================================
# # 🌐 CORS Configuration
# # =========================================
# allowed_origins = [
#     "https://teamflow-frontend-omega.vercel.app",
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=allowed_origins,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
#     allow_headers=["*"],
#     expose_headers=["*"]
# )

# # =========================================
# # 📦 Routers
# # =========================================
# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# app.include_router(project_router, prefix="/projects", tags=["Projects"])
# app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
# app.include_router(users_router, prefix="/users", tags=["Users"])       
# app.include_router(invitation_router, prefix="/auth", tags=["Invitations"])
# app.include_router(profile_router, tags=["Profile"]) 

# # Fix payment router - only include once with proper prefix
# app.include_router(payment_router, prefix="/api/v1", tags=["Payments"])

# # Serve the entire uploads directory at /static
# app.mount("/static", StaticFiles(directory="uploads"), name="static")

# # =========================================
# # 🩺 Health Check
# # =========================================
# @app.get("/health")
# def health_check():
#     return {
#         "status": "ok", 
#         "message": "Backend is running",
#         "timestamp": "2024-01-01T00:00:00Z"  # You might want to use datetime.utcnow()
#     }


# @app.get("/")
# def read_root():
#     return {"message": "Welcome to TeamFlow Backend!"}


# # =========================================
# # 🔧 Additional CORS handling for preflight requests
# # =========================================
# @app.options("/{rest_of_path:path}")
# async def preflight_handler(rest_of_path: str):
#     return {"message": "CORS preflight"}


# @app.middleware("http")
# async def add_cors_headers(request, call_next):
#     response = await call_next(request)
    
#     # Ensure CORS headers are always present
#     origin = request.headers.get("origin")
#     if origin in allowed_origins:
#         response.headers["Access-Control-Allow-Origin"] = origin
#         response.headers["Access-Control-Allow-Credentials"] = "true"
#         response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
#         response.headers["Access-Control-Allow-Headers"] = "*"
    
#     return response