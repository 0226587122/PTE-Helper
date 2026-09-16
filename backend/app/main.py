import logging

from fastapi import FastAPI

from app.api import admin, auth, general, sets
from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="PTE Practice API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.include_router(general.router)
app.include_router(auth.router)
app.include_router(sets.router)
app.include_router(admin.router)
