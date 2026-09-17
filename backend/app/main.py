import logging

from fastapi import FastAPI

from app.api import admin, auth, general, sets
from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if settings.is_production:
    if settings.jwt_secret == "change-me-in-production" or len(settings.jwt_secret) < 32:
        raise RuntimeError("Set JWT_SECRET to a long random value (at least 32 characters) in production.")
    if not settings.cookie_secure:
        raise RuntimeError("COOKIE_SECURE must be true in production.")

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
