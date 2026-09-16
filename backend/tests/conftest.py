"""Test setup.

Database tests run against a real MySQL 8 server (TEST_DATABASE_URL), never SQLite, so JSON columns and the
primary key rule behave like production. Pure scoring tests don't touch the database at all.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["COOKIE_SECURE"] = "false"
os.environ["JWT_SECRET"] = "test-secret"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("DATABASE_CA_CERT", None)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.bank.validation import content_hash  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import get_engine, session_factory  # noqa: E402
from app.models import ContentSource, Question, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from scripts.seed import upsert_task_types  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
TABLES = [
    "question_reports", "ai_feedback", "set_questions", "practice_sets", "questions", "content_sources",
    "task_types", "users",
]


@pytest.fixture(scope="session")
def migrated() -> Iterator[None]:
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to a MySQL 8 database to run database tests.")
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in TABLES + ["alembic_version"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(config, "head")
    yield


@pytest.fixture
def db(migrated) -> Iterator[Session]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in TABLES:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    session = session_factory()()
    upsert_task_types(session)
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db) -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def settings():
    return get_settings()


def make_user(db: Session, email: str = "student@example.com", role: str = "student", password: str = "password123") -> User:
    user = User(email=email, display_name="Test Student", password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    return user


def signed_in_client(client: TestClient, db: Session, email: str = "student@example.com", role: str = "student") -> User:
    user = make_user(db, email=email, role=role)
    response = client.post("/api/auth/signin", json={"email": email, "password": "password123"})
    assert response.status_code == 200, response.text
    return user


def make_wfd_questions(db: Session, count: int, status: str = "active", start: int = 0) -> list[Question]:
    questions = []
    for i in range(start, start + count):
        payload = {"sentence": f"Students in group {i} reviewed the lecture notes before the seminar."}
        question = Question(
            task_type_code="WFD", payload=payload, content_hash=content_hash("WFD", None, payload),
            status=status, report_count=0, times_served=0,
        )
        db.add(question)
        questions.append(question)
    db.commit()
    return questions


def make_lecture(db: Session, key: str = "lecture-test") -> ContentSource:
    body = (
        "Urban trees do far more than make streets look attractive. Researchers who measured temperatures across "
        "several cities found that neighbourhoods with dense canopy cover were up to four degrees cooler on summer "
        "afternoons. Trees also slow stormwater, because leaves intercept rain and roots help soil absorb it. "
        "However, the benefits are not shared equally. Wealthier suburbs usually have more trees, while older "
        "industrial areas have fewer. Planners in Melbourne and Auckland now map canopy cover street by street so "
        "that new planting can be targeted where heat risk is highest. The speaker concludes that tree planting "
        "should be treated as essential public infrastructure."
    )
    source = ContentSource(source_key=key, kind="lecture", title="Urban trees", body=body)
    db.add(source)
    db.commit()
    return source
