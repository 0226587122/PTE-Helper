"""Database engine and session handling."""

import ssl
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings, url: str | None = None) -> Engine:
    connect_args: dict = {}
    if settings.database_ca_cert:
        # DigitalOcean hands over the CA certificate as PEM text, so load it straight into a context.
        context = ssl.create_default_context(cadata=settings.database_ca_cert.replace("\\n", "\n"))
        connect_args["ssl"] = context
    elif settings.is_production:
        raise RuntimeError("DATABASE_CA_CERT must be set in production so the database connection uses SSL.")
    return create_engine(
        url or settings.database_url,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle,
        pool_size=settings.db_pool_size,
        connect_args=connect_args,
        future=True,
    )


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        _engine = build_engine(get_settings())
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()
