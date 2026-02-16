"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.templating import Jinja2Templates

from app.api import auth, directors, reports, items, settings, admin
from app.database import engine, Base

# Import Celery tasks to ensure they're registered
from app.worker import tasks  # noqa: F401

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Director Media Monitoring", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(directors.router, prefix="/api/directors", tags=["directors"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include web UI routes
from app.api import web

app.include_router(web.router, tags=["web"])


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


