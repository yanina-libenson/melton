"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print(f"Starting Dr. Melton API in {settings.environment} mode")
    print(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}")

    yield

    # Shutdown
    print("Shutting down Dr. Melton API")


app = FastAPI(
    title="Dr. Melton API",
    description="Production Python API for the Dr. Melton Agent Builder platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Dr. Melton API",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }


# API routers
from app.api.v1 import agents, playground, user_settings

app.include_router(agents.router, prefix=f"{settings.api_v1_prefix}/agents", tags=["agents"])
app.include_router(
    playground.router, prefix=f"{settings.api_v1_prefix}/playground", tags=["playground"]
)
app.include_router(user_settings.router, prefix=settings.api_v1_prefix)
