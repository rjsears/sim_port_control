# =============================================================================
# SimPortControl - Main Application
# =============================================================================
"""
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, discovery, logs, ports, simulators, switches, system, users
from app.services.scheduler import get_scheduler_service

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting SimPortControl...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start scheduler
    scheduler = get_scheduler_service()
    scheduler.start()
    logger.info("Scheduler started")

    # Restore any scheduled jobs from database (for enabled ports)
    await scheduler.restore_scheduled_jobs()

    # Create default admin user if not exists
    await create_default_admin()

    # Warn if using default admin password
    if settings.admin_password == "changeme":
        logger.warning(
            "⚠️  SECURITY WARNING: Using default admin password! "
            "Change ADMIN_PASSWORD environment variable in production."
        )

    logger.info(f"SimPortControl ready - {settings.domain}")

    yield

    # Shutdown
    logger.info("Shutting down SimPortControl...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")


async def create_default_admin():
    """Create default admin user if none exists."""
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.user import User
    from app.services.auth import AuthService

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.role == "admin"))
        admin = result.scalars().first()

        if not admin:
            logger.info("Creating default admin user...")
            admin = User(
                username=settings.admin_username,
                password_hash=AuthService.get_password_hash(settings.admin_password),
                role="admin",
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Default admin user '{settings.admin_username}' created")
        else:
            logger.info(f"Admin user already exists: {admin.username}")


# Create FastAPI application
app = FastAPI(
    title="SimPortControl",
    description="Web-based switch port management for flight simulators",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{settings.domain}",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(simulators.router, prefix="/api")
app.include_router(switches.router, prefix="/api")
app.include_router(ports.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "name": "SimPortControl API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


# Health check at root level
@app.get("/health")
async def root_health():
    """Root health check for load balancers."""
    return {"status": "ok"}
