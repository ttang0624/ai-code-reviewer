# Entry point for the FastAPI application.
# Creates the app instance and registers all routes.

from fastapi import FastAPI
from app.routes import webhook

app = FastAPI()

app.include_router(webhook.router)
