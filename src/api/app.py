"""FastAPI application for SIH-Compliance-AI."""
from fastapi import FastAPI

from .routes import router


app = FastAPI(title="SIH Compliance AI API", version="0.1.0")
app.include_router(router)


__all__ = ["app"]
