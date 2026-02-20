"""FastAPI application for Suksham Vachak."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from suksham_vachak.logging import configure_logging, get_logger

from .middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from .routes import router

# Load environment variables from .env file (before any config reads below)
load_dotenv()

# Configure logging based on environment
env = os.getenv("LOG_ENV", "development")
level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(env=env, level=level)

logger = get_logger(__name__)

app = FastAPI(
    title="Suksham Vachak API",
    description="The Subtle Commentator - AI-powered cricket commentary",
    version="0.1.0",
)

# Add logging middleware (order matters - correlation ID first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sukshamvachak.com",
        "https://www.sukshamvachak.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

logger.info("Suksham Vachak API initialized", env=env, log_level=level)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Suksham Vachak",
        "tagline": "The Subtle Commentator",
        "version": "0.1.0",
        "docs": "/docs",
    }
