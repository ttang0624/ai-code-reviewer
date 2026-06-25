from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database.connection import init_db
from app.routes import webhook


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="GitHub pull request webhook service that posts AI-generated code reviews.",
    lifespan=lifespan,
)


app.include_router(webhook.router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
        "ai_configured": bool(settings.anthropic_api_key),
        "github_configured": bool(settings.github_token),
    }
