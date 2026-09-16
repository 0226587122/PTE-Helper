"""Random draw, backup top-up and backup promotion, against real MySQL."""

from sqlalchemy import select

from app.config import get_settings
from app.models import Question, QuestionReport
from app.services import pool
from app.services.draw import create_set
from tests.conftest import make_user, make_wfd_questions, signed_in_client
from tests.test_bank import ANSWER_KEYS, _walk_keys


def _ids(practice_set):
    return [sq.question_id for sq in practice_set.questions]


def test_set_has_15_random_active_questions(db):
    user = make_user(db)
    make_wfd_questions(db, 40, "active")
    make_wfd_questions(db, 15, "backup", start=100)
    practice_set = create_set(db, user, "WFD")
    db.commit()
    assert get_settings().questions_per_set == 15
    assert practice_set.question_count == 15
    assert len(set(_ids(practice_set))) == 15
    assert [sq.position for sq in practice_set.questions] == list(range(1, 16))
    assert not any(sq.drew_from_backup for sq in practice_set.questions)
    statuses = set(db.scalars(select(Question.status).where(Question.id.in_(_ids(practice_set)))))
    assert statuses == {"active"}


def test_draw_is_random(db):
    user = make_user(db)
    make_wfd_questions(db, 60, "active")
    first = set(_ids(create_set(db, user, "WFD")))
    other = make_user(db, email="other@example.com")
    second = set(_ids(create_set(db, other, "WFD")))
    assert first != second


def test_no_repeats_from_last_three_sets(db):
    user = make_user(db)
    make_wfd_questions(db, 60, "active")
    seen: set[int] = set()
    for _ in range(3):
        ids = set(_ids(create_set(db, user, "WFD")))
        assert not ids & seen
        seen |= ids
    db.commit()
    # The 4th set may reuse questions from the 1st set (which is no longer in the last 3), but nothing from sets 2-3.
    fourth = create_set(db, user, "WFD")
    assert len(set(_ids(fourth))) == 15


def test_backup_tops_up_when_active_runs_out(db):
    user = make_user(db)
    make_wfd_questions(db, 20, "active")
    backups = make_wfd_questions(db, 20, "backup", start=100)
    backup_ids = {q.id for q in backups}
    create_set(db, user, "WFD")  # uses 15 of the 20 active
    second = create_set(db, user, "WFD")
    from_backup = [sq for sq in second.questions if sq.drew_from_backup]
    assert len(from_backup) == 10
    assert {sq.question_id for sq in from_backup} <= backup_ids
    assert len(set(_ids(second))) == 15


def test_repeats_allowed_when_pool_is_short(db, caplog):
    user = make_user(db)
    make_wfd_questions(db, 10, "active")
    make_wfd_questions(db, 2, "backup", start=100)
    create_set(db, user, "WFD")
    with caplog.at_level("WARNING"):
        practice_set = create_set(db, user, "WFD")
    assert practice_set.question_count == 15
    assert "allowing repeats" in caplog.text


def test_reported_and_retired_questions_are_left_out(db):
    user = make_user(db)
    active = make_wfd_questions(db, 20, "active")
    make_wfd_questions(db, 5, "retired", start=200)
    reported = active[:5]
    for q in reported:
        db.add(QuestionReport(question_id=q.id, user_id=user.id, reason="typo"))
    db.commit()
    practice_set = create_set(db, user, "WFD")
    ids = set(_ids(practice_set))
    assert not ids & {q.id for q in reported}
    assert set(db.scalars(select(Question.status).where(Question.id.in_(ids)))) == {"active"}


def test_retire_promotes_oldest_backup(db):
    make_wfd_questions(db, 30, "active")
    backups = make_wfd_questions(db, 3, "backup", start=100)
    target = db.scalars(select(Question).where(Question.status == "active")).first()
    promoted = pool.retire_question(db, target)
    db.commit()
    assert target.status == "retired" and target.retired_at is not None
    assert [q.id for q in promoted] == [backups[0].id]
    assert pool.active_count(db, "WFD") == 30


def test_no_promotion_when_pool_is_already_big_enough(db):
    make_wfd_questions(db, 35, "active")
    make_wfd_questions(db, 3, "backup", start=100)
    target = db.scalars(select(Question).where(Question.status == "active")).first()
    assert pool.retire_question(db, target) == []


def test_reports_retire_question_at_threshold(db):
    questions = make_wfd_questions(db, 30, "active")
    make_wfd_questions(db, 2, "backup", start=100)
    target = questions[0]
    for i in range(get_settings().report_retire_threshold):
        user = make_user(db, email=f"r{i}@example.com")
        _, retired = pool.report_question(db, target, user, "The audio doesn't match")
    db.commit()
    assert retired is True
    assert target.status == "retired"
    assert target.report_count == 3
    assert pool.active_count(db, "WFD") == 30


class TestApi:
    def test_full_flow_without_leaking_answers(self, client, db):
        signed_in_client(client, db)
        make_wfd_questions(db, 30, "active")

        created = client.post("/api/sets", json={"task_type": "WFD"})
        assert created.status_code == 201, created.text
        data = created.json()
        assert data["question_count"] == 15

        question = client.get(f"/api/sets/{data['id']}/questions/1").json()
        assert question["answered"] is False
        assert question["answer"] is None and question["result"] is None
        assert not ANSWER_KEYS & set(_walk_keys(question["display"]))

        sentence = question["display"]["audio"]
        answered = client.post(f"/api/sets/{data['id']}/questions/1/answer", json={"response": {"text": sentence}})
        assert answered.status_code == 200, answered.text
        body = answered.json()
        assert body["result"]["pct"] == 100.0
        assert body["answer"]["sentence"] == sentence

        again = client.post(f"/api/sets/{data['id']}/questions/1/answer", json={"response": {"text": "x"}})
        assert again.status_code == 409

        finished = client.post(f"/api/sets/{data['id']}/finish").json()
        # One perfect answer out of 15, the rest count as zero.
        assert finished["average_pct"] == round(100 / 15, 1)
        assert finished["estimated_score"] == 15

        progress = client.get("/api/me/progress").json()
        assert progress["types"][0]["code"] == "WFD"
        assert progress["recent"][0]["estimated_score"] == 15

    def test_other_users_cannot_see_a_set(self, client, db):
        owner = make_user(db, email="owner@example.com")
        make_wfd_questions(db, 20, "active")
        practice_set = create_set(db, owner, "WFD")
        db.commit()
        signed_in_client(client, db, email="snoop@example.com")
        assert client.get(f"/api/sets/{practice_set.id}/questions/1").status_code == 404

    def test_report_endpoint(self, client, db):
        signed_in_client(client, db)
        make_wfd_questions(db, 20, "active")
        set_id = client.post("/api/sets", json={"task_type": "WFD"}).json()["id"]
        qid = client.get(f"/api/sets/{set_id}/questions/1").json()["question_id"]
        assert client.post(f"/api/questions/{qid}/report", json={"reason": "Audio is unclear"}).status_code == 201
        # A second report from the same person doesn't count twice.
        client.post(f"/api/questions/{qid}/report", json={"reason": "Still unclear"})
        assert db.get(Question, qid).report_count == 1

    def test_cannot_report_unseen_question(self, client, db):
        signed_in_client(client, db)
        q = make_wfd_questions(db, 1, "active")[0]
        assert client.post(f"/api/questions/{q.id}/report", json={"reason": "bad"}).status_code == 404

    def test_admin_retire_via_api_promotes_backup(self, client, db):
        signed_in_client(client, db, email="admin@example.com", role="admin")
        active = make_wfd_questions(db, 30, "active")
        backup = make_wfd_questions(db, 1, "backup", start=100)[0]
        response = client.patch(f"/api/admin/questions/{active[0].id}", json={"status": "retired"})
        assert response.status_code == 200, response.text
        assert response.json()["promoted_ids"] == [backup.id]
        summary = {row["code"]: row for row in client.get("/api/admin/summary").json()}
        assert summary["WFD"]["active"] == 30
        assert summary["WFD"]["retired"] == 1

    def test_admin_payload_edit_is_validated(self, client, db):
        signed_in_client(client, db, email="admin@example.com", role="admin")
        q = make_wfd_questions(db, 1, "active")[0]
        bad = client.patch(f"/api/admin/questions/{q.id}", json={"payload": {"sentence": "Too short."}})
        assert bad.status_code == 422
        good_sentence = "Researchers compared rainfall records from forty weather stations across the region."
        ok = client.patch(f"/api/admin/questions/{q.id}", json={"payload": {"sentence": good_sentence}})
        assert ok.status_code == 200
        assert ok.json()["payload"]["sentence"] == good_sentence

    def test_admin_list_filters(self, client, db):
        signed_in_client(client, db, email="admin@example.com", role="admin")
        make_wfd_questions(db, 3, "active")
        make_wfd_questions(db, 2, "backup", start=100)
        page = client.get("/api/admin/questions", params={"task_type": "WFD", "status": "backup"}).json()
        assert page["total"] == 2
        search = client.get("/api/admin/questions", params={"search": "group 100"}).json()
        assert search["total"] == 1
