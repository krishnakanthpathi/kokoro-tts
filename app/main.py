import sys
import os

# Ensure the parent directory is in sys.path so we can import from 'app'
# and also import the local 'kokoro' directory from the root level.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import router as api_router
from app.api.admin_endpoints import router as admin_router
from app.config import settings
from app.database import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    print("Initializing SQLite database...")
    init_db()

# Root entry point
@app.get("/")
def root_entry_point():
    return {"message": "welcome kokoro service"}

# Include API and Admin routes
# Note: router endpoints are added first to take precedence over the static files mount
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix="/admin")

# Mount Static Admin Dashboard UI at /admin
static_dir = os.path.join(current_dir, "static")
if os.path.exists(static_dir):
    print(f"Mounting static files from: {static_dir} at /admin")
    app.mount("/admin", StaticFiles(directory=static_dir, html=True), name="admin")
else:
    print(f"Warning: Static files directory not found at: {static_dir}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
