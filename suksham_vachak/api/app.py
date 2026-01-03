"""FastAPI application for Suksham Vachak."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="Suksham Vachak API",
    description="The Subtle Commentator - AI-powered cricket commentary",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Suksham Vachak",
        "tagline": "The Subtle Commentator",
        "version": "0.1.0",
        "docs": "/docs",
    }
