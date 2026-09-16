from types import SimpleNamespace

import pytest

from app.bank.validation import content_hash
from app.config import get_settings
from app.models import Question
from app.services import feedback as feedback_service
from tests.conftest import signed_in_client


class FakeMessages:
    calls = 0

    def parse(self, **kwargs):
        FakeMessages.calls += 1
        assert kwargs["model"] == get_settings().anthropic_model
        assert "PTE Academic examiner" in kwargs["system"]
        assert kwargs["output_format"] is feedback_service.ExaminerFeedback
        parsed = feedback_service.ExaminerFeedback(
            score=72,
            traits=[{"name": "Content", "score": 2, "max": 3, "comment": "Covers the main idea."}],
            strengths=["Clear position"],
            improvements=["Add an example"],
            model_answer="Free public transport can reduce congestion...",
        )
        return SimpleNamespace(parsed_output=parsed, stop_reason="end_turn", model=kwargs["model"])


class FakeClient:
    def __init__(self, **kwargs):
        self.messages = FakeMessages()


@pytest.fixture
def fake_claude(monkeypatch):
    FakeMessages.calls = 0
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(feedback_service.anthropic, "Anthropic", FakeClient)
    return FakeMessages


def _essay_question(db):
    payload = {
        "prompt": "Some people believe that governments should make public transport free for everyone. Discuss.",
        "key_points": ["free public transport", "cost to government", "congestion"],
    }
    db.add(Question(task_type_code="WE", payload=payload, content_hash=content_hash("WE", None, payload), status="active", report_count=0, times_served=0))
    db.commit()


def _answered_essay(client):
    set_id = client.post("/api/sets", json={"task_type": "WE"}).json()["id"]
    answered = client.post(f"/api/sets/{set_id}/questions/1/answer", json={"response": {"text": "Free transport is good."}})
    return answered.json()["set_question_id"]


def test_feedback_is_created_and_cached(client, db, fake_claude):
    signed_in_client(client, db)
    _essay_question(db)
    sq_id = _answered_essay(client)
    first = client.post(f"/api/set-questions/{sq_id}/feedback")
    assert first.status_code == 200, first.text
    assert first.json()["score"] == 72
    second = client.post(f"/api/set-questions/{sq_id}/feedback")
    assert second.json() == first.json()
    assert fake_claude.calls == 1


def test_daily_limit(client, db, fake_claude, monkeypatch):
    monkeypatch.setattr(get_settings(), "feedback_daily_limit", 2)
    signed_in_client(client, db)
    _essay_question(db)
    set_id = client.post("/api/sets", json={"task_type": "WE"}).json()["id"]
    # The single WE question repeats to fill the set, so each position is a separate answer.
    ids = []
    for position in (1, 2, 3):
        r = client.post(f"/api/sets/{set_id}/questions/{position}/answer", json={"response": {"text": "Some text."}})
        ids.append(r.json()["set_question_id"])
    assert client.post(f"/api/set-questions/{ids[0]}/feedback").status_code == 200
    assert client.post(f"/api/set-questions/{ids[1]}/feedback").status_code == 200
    limited = client.post(f"/api/set-questions/{ids[2]}/feedback")
    assert limited.status_code == 429
    assert "used all 2" in limited.json()["detail"]


def test_feedback_needs_an_answer(client, db, fake_claude):
    signed_in_client(client, db)
    _essay_question(db)
    set_id = client.post("/api/sets", json={"task_type": "WE"}).json()["id"]
    sq_id = client.get(f"/api/sets/{set_id}/questions/1").json()["set_question_id"]
    assert client.post(f"/api/set-questions/{sq_id}/feedback").status_code == 409


def test_feedback_not_offered_for_objective_types(client, db, fake_claude):
    from tests.conftest import make_wfd_questions

    signed_in_client(client, db)
    make_wfd_questions(db, 15)
    set_id = client.post("/api/sets", json={"task_type": "WFD"}).json()["id"]
    sq_id = client.post(f"/api/sets/{set_id}/questions/1/answer", json={"response": {"text": "hi"}}).json()["set_question_id"]
    assert client.post(f"/api/set-questions/{sq_id}/feedback").status_code == 400


def test_missing_api_key_gives_clear_message(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    signed_in_client(client, db)
    _essay_question(db)
    sq_id = _answered_essay(client)
    response = client.post(f"/api/set-questions/{sq_id}/feedback")
    assert response.status_code == 503
    assert "isn't set up" in response.json()["detail"]
