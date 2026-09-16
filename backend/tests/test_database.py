"""Schema, config and seed/export checks against real MySQL."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select, text

from app.config import normalise_database_url
from app.db import Base, get_engine
from app.models import ContentSource, Question
from scripts.export_bank import export
from scripts.seed import seed
from tests.samples import sample_bank


def test_every_table_has_a_primary_key(db):
    rows = db.execute(
        text(
            """
            SELECT t.table_name
            FROM information_schema.tables t
            LEFT JOIN information_schema.table_constraints c
              ON c.table_schema = t.table_schema AND c.table_name = t.table_name AND c.constraint_type = 'PRIMARY KEY'
            WHERE t.table_schema = DATABASE() AND t.table_type = 'BASE TABLE' AND c.constraint_name IS NULL
            """
        )
    ).all()
    assert rows == []


def test_tables_use_innodb_and_utf8mb4(db):
    rows = db.execute(
        text("SELECT table_name, engine, table_collation FROM information_schema.tables WHERE table_schema = DATABASE()")
    ).all()
    assert rows
    for name, engine, collation in rows:
        assert engine == "InnoDB", name
        assert collation.startswith("utf8mb4"), name


def test_migrations_match_models(db):
    with get_engine().connect() as conn:
        diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diffs == [], diffs


def test_database_url_conversion():
    url = normalise_database_url("mysql://doadmin:secret@db-host:25060/defaultdb?ssl-mode=REQUIRED")
    assert url == "mysql+pymysql://doadmin:secret@db-host:25060/defaultdb?charset=utf8mb4"
    assert normalise_database_url("mysql+pymysql://a:b@h/d?charset=utf8mb4").endswith("?charset=utf8mb4")


def test_seed_is_safe_to_run_twice(db):
    sources, questions = sample_bank()
    first = seed(db, sources, questions)
    db.commit()
    assert first["questions_added"] == len(questions)
    second = seed(db, sources, questions)
    db.commit()
    assert second["questions_added"] == 0
    assert second["questions_unchanged"] == len(questions)
    assert db.scalar(select(func.count()).select_from(Question)) == len(questions)
    assert db.scalar(select(func.count()).select_from(ContentSource)) == len(sources)


def test_reseed_keeps_admin_status_changes(db):
    sources, questions = sample_bank()
    seed(db, sources, questions)
    db.commit()
    question = db.scalars(select(Question).where(Question.task_type_code == "WFD")).one()
    question.status = "retired"
    db.commit()
    seed(db, sources, questions)
    db.commit()
    db.refresh(question)
    assert question.status == "retired"


def test_export_round_trip(db):
    sources, questions = sample_bank()
    seed(db, sources, questions)
    db.commit()
    exported = export(db)
    assert len(exported["sources"]) == len(sources)
    assert len(exported["questions"]) == len(questions)
    # Re-seeding the export adds nothing new.
    again = seed(db, exported["sources"], exported["questions"])
    assert again["questions_added"] == 0


def test_json_columns_round_trip_unicode(db):
    sources, questions = sample_bank()
    seed(db, sources, questions)
    db.commit()
    source = db.scalars(select(ContentSource).where(ContentSource.kind == "discussion")).one()
    source.turns = [{"speaker": "Aroha", "text": "Kia ora — ngā mihi, café ☕"}]
    db.commit()
    db.expire_all()
    assert db.get(ContentSource, source.id).turns[0]["text"] == "Kia ora — ngā mihi, café ☕"
