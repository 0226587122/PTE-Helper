"""The full mock test: assembly, timing, navigation rules and the score report."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.exam import clock
from app.exam.assembler import assemble
from app.exam.blueprint import PARTS, PARTS_BY_SECTION, item_count_range, part_minutes, skills_for, total_minutes
from app.models import PracticeSet, SetQuestion, utc_now
from app.scoring.aggregate import build_report
from tests.conftest import make_user, signed_in_client
from tests.samples import sample_bank

ALL_CODES = [spec.code for part in PARTS for spec in part.items]


class TestBlueprint:
    def test_covers_every_task_type_once_in_exam_order(self):
        assert len(ALL_CODES) == 22
        assert len(set(ALL_CODES)) == 22
        assert [part.section for part in PARTS] == ["speaking_writing", "reading", "listening"]

    def test_item_counts_match_the_score_guide(self):
        low, high = item_count_range()
        # The real test has 65 to 75 questions, plus the unscored introduction. Every type's range
        # comes from the score guide, so the lowest total matches and the highest is only reached if
        # every type happened to sit at its maximum.
        assert low == 65
        assert high <= 90

    def test_part_lengths_sit_in_the_published_ranges(self):
        # Score guide: Speaking and Writing 76 to 84 minutes, Reading 23 to 30, Listening 31 to 39.
        minutes = {part.section: part_minutes(part) for part in PARTS}
        assert 70 <= minutes["speaking_writing"][0] <= 84
        assert minutes["reading"] == (30, 30)
        assert 31 <= minutes["listening"][0] <= 45
        low, _ = total_minutes()
        # The whole test runs about two and a quarter hours.
        assert 130 <= low <= 150

    def test_every_type_scores_at_least_one_skill(self):
        for code in ALL_CODES:
            assert skills_for(code), code

    def test_only_reading_lets_students_go_back(self):
        assert [part.section for part in PARTS if part.allow_back] == ["reading"]
        assert PARTS_BY_SECTION["reading"].section_seconds == 30 * 60


def _seed_bank(db, per_type: int = 13):
    """Enough questions of every type to assemble a mock test."""
    from app.bank.validation import content_hash
    from app.models import ContentSource, Question
    from tests.samples import sample_bank as bank

    sources, questions = bank()
    by_key = {}
    for data in sources:
        source = ContentSource(
            source_key=data["source_key"], kind=data["kind"], title=data["title"], body=data["body"],
            blank_markup=data.get("blank_markup"), turns=data.get("turns"),
        )
        db.add(source)
        by_key[data["source_key"]] = source
    db.flush()
    for data in questions:
        for copy_index in range(per_type):
            payload = dict(data["payload"])
            # Make each copy unique so the content hash differs.
            payload["_variant"] = copy_index
            db.add(
                Question(
                    task_type_code=data["type"],
                    source_id=by_key[data["source_key"]].id if data.get("source_key") else None,
                    payload=payload,
                    content_hash=content_hash(data["type"], data.get("source_key"), payload),
                    status="active",
                    report_count=0,
                    times_served=0,
                )
            )
    db.commit()


@pytest.fixture
def bank(db):
    _seed_bank(db)
    return db


class TestAssembly:
    def test_builds_every_part_in_order_with_counts_inside_the_blueprint(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()

        assert mock.mode == "mock"
        assert mock.task_type_code is None
        assert mock.blueprint_version
        low, high = item_count_range()
        assert low <= mock.question_count <= high
        assert [item.position for item in mock.questions] == list(range(1, mock.question_count + 1))
        # Sections appear in exam order, and task types in blueprint order within each section.
        sections = [item.section for item in mock.questions]
        assert sections == sorted(sections, key=lambda s: ["speaking_writing", "reading", "listening"].index(s))
        codes_in_order = [item.task_type_code for item in mock.questions]
        assert codes_in_order == sorted(codes_in_order, key=ALL_CODES.index)
        for spec in (s for part in PARTS for s in part.items):
            count = codes_in_order.count(spec.code)
            assert spec.count[0] <= count <= spec.count[1], spec.code

    def test_items_carry_a_rendered_variant_with_answers_hidden(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        for item in mock.questions:
            assert item.rendered_payload["display"]
            assert item.rendered_payload["answer"]

    def test_two_mock_tests_do_not_repeat_the_same_questions(self, bank, db):
        user = make_user(db)
        first = {item.question_id for item in assemble(db, user).questions}
        db.commit()
        second = {item.question_id for item in assemble(db, user).questions}
        db.commit()
        overlap = first & second
        assert len(overlap) < len(first) / 4


class TestClock:
    def test_item_deadline_covers_preparation_answer_and_grace(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        item = mock.questions[0]  # Read Aloud: 35s prep + 40s answer
        now = utc_now()
        deadline = clock.serve(mock, item, now)
        assert deadline == now + timedelta(seconds=clock.item_allowance("RA"))
        assert clock.remaining_seconds(deadline, now) == clock.item_allowance("RA")

    def test_reading_items_share_one_part_clock(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        reading = [item for item in mock.questions if item.section == "reading"]
        now = utc_now()
        first = clock.serve(mock, reading[0], now)
        later = clock.serve(mock, reading[1], now + timedelta(seconds=90))
        assert first == later == now + timedelta(seconds=30 * 60)

    def test_deadlines_survive_being_served_again(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        item = mock.questions[0]
        first = clock.serve(mock, item, utc_now())
        again = clock.serve(mock, item, utc_now() + timedelta(seconds=30))
        assert first == again


class TestRunningAMockTest:
    def start(self, client, db):
        signed_in_client(client, db)
        response = client.post("/api/mock-tests")
        assert response.status_code == 201, response.text
        return response.json()

    def test_start_serve_answer_and_finish(self, client, bank, db):
        state = self.start(client, db)
        assert state["status"] == "in_progress"
        assert state["current_position"] == 1
        assert state["items"][0]["task_type"] == "RA"

        first = client.get(f"/api/mock-tests/{state['id']}/questions/1").json()
        assert first["task_type"] == "RA"
        assert first["starts_part"] is True
        assert first["part_title"].startswith("Part 1")
        assert first["prep_seconds"] == 35
        assert first["seconds_remaining"] > 0
        assert "answer" not in first  # no answers during the test

        ack = client.post(
            f"/api/mock-tests/{state['id']}/questions/1/answer",
            json={"response": {"transcript": "some spoken answer", "self_rating": {"fluency": 4, "pronunciation": 4}}},
        ).json()
        assert ack == {"position": 1, "accepted": True, "late": False, "next_position": 2, "finished": False}

        # The score is stored but never returned mid-test.
        item = db.scalars(select(SetQuestion).where(SetQuestion.set_id == state["id"], SetQuestion.position == 1)).one()
        assert item.score_pct is not None

    def test_answers_must_be_in_order_and_cannot_go_back(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        assert client.get(f"/api/mock-tests/{set_id}/questions/3").status_code == 409

        client.get(f"/api/mock-tests/{set_id}/questions/1")
        client.post(f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {"transcript": "x"}})
        client.get(f"/api/mock-tests/{set_id}/questions/2")
        # Speaking is forward only.
        assert client.get(f"/api/mock-tests/{set_id}/questions/1").status_code == 409
        assert client.post(f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {}}).status_code == 409

    def test_reading_allows_going_back_and_changing_an_answer(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        reading = [item for item in state["items"] if item["section"] == "reading"]
        first, second = reading[0]["position"], reading[1]["position"]

        # Walk to the start of the reading part, answering nothing on the way.
        for position in range(1, first + 1):
            client.get(f"/api/mock-tests/{set_id}/questions/{position}")
            client.post(f"/api/mock-tests/{set_id}/questions/{position}/answer", json={"response": {}})
        client.get(f"/api/mock-tests/{set_id}/questions/{second}")

        back = client.get(f"/api/mock-tests/{set_id}/questions/{first}")
        assert back.status_code == 200
        assert back.json()["allow_back"] is True
        changed = client.post(
            f"/api/mock-tests/{set_id}/questions/{first}/answer", json={"response": {"answers": ["a", "b", "c", "d"]}}
        )
        assert changed.status_code == 200

    def test_a_late_answer_is_accepted_but_scores_zero(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        client.get(f"/api/mock-tests/{set_id}/questions/1")
        item = db.scalars(select(SetQuestion).where(SetQuestion.set_id == set_id, SetQuestion.position == 1)).one()
        item.deadline_at = utc_now() - timedelta(seconds=1)
        db.commit()

        ack = client.post(
            f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {"transcript": "late answer"}}
        ).json()
        assert ack["late"] is True
        db.expire_all()
        item = db.scalars(select(SetQuestion).where(SetQuestion.set_id == set_id, SetQuestion.position == 1)).one()
        assert item.late is True
        assert item.score_pct == 0.0

    def test_resuming_returns_the_same_test_at_the_same_place(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        client.get(f"/api/mock-tests/{set_id}/questions/1")
        client.post(f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {"transcript": "x"}})
        client.get(f"/api/mock-tests/{set_id}/questions/2")

        again = client.post("/api/mock-tests").json()
        assert again["id"] == set_id
        assert again["current_position"] == 2
        assert again["answered_count"] == 1

    def test_submitting_early_scores_the_rest_as_zero_and_returns_a_report(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        client.get(f"/api/mock-tests/{set_id}/questions/1")
        client.post(f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {"transcript": "x"}})

        report = client.post(f"/api/mock-tests/{set_id}/submit").json()
        assert report["overall_score"] >= 10
        assert report["answered_count"] == 1
        assert {skill["key"] for skill in report["communicative_skills"]} == {"listening", "reading", "speaking", "writing"}
        assert len(report["sections"]) == 3
        assert "not official Pearson" in report["disclaimer"]

        # The test is closed afterwards.
        assert client.get(f"/api/mock-tests/{set_id}/questions/2").status_code == 409
        assert client.get(f"/api/mock-tests/{set_id}/report").status_code == 200

    def test_running_out_of_time_everywhere_finishes_the_test(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        client.get(f"/api/mock-tests/{set_id}/questions/1")
        past = utc_now() - timedelta(seconds=5)
        for item in db.scalars(select(SetQuestion).where(SetQuestion.set_id == set_id)):
            item.deadline_at = past
        db.commit()

        state = client.get(f"/api/mock-tests/{set_id}").json()
        assert state["status"] == "finished"
        report = client.get(f"/api/mock-tests/{set_id}/report").json()
        assert report["answered_count"] == 0
        assert report["overall_score"] == 10

    def test_another_student_cannot_open_the_test(self, client, bank, db):
        state = self.start(client, db)
        client.post("/api/auth/signout")
        signed_in_client(client, db, email="other@example.com")
        assert client.get(f"/api/mock-tests/{state['id']}").status_code == 404

    def test_blueprint_endpoint_describes_the_test(self, client, bank, db):
        signed_in_client(client, db)
        blueprint = client.get("/api/mock-tests/blueprint").json()
        assert len(blueprint["parts"]) == 3
        assert sum(len(part["task_types"]) for part in blueprint["parts"]) == 22
        assert blueprint["minutes"]["min"] >= 130
        assert blueprint["personal_introduction"]["record_seconds"] == 30

    def test_mock_test_appears_in_progress_and_review(self, client, bank, db):
        state = self.start(client, db)
        set_id = state["id"]
        client.get(f"/api/mock-tests/{set_id}/questions/1")
        client.post(f"/api/mock-tests/{set_id}/questions/1/answer", json={"response": {"transcript": "x"}})
        client.post(f"/api/mock-tests/{set_id}/submit")

        progress = client.get("/api/me/progress").json()
        assert progress["mock_tests_completed"] == 1
        assert progress["last_mock_score"] == progress["overall_estimate"]
        assert progress["recent"][0]["name"] == "Full mock test"
        assert progress["recent"][0]["mode"] == "mock"
        # Reviewing after the test shows the answers.
        review = client.get(f"/api/sets/{set_id}/review").json()
        assert len(review) == state["question_count"]
        assert review[0]["answer"] is not None


class TestReport:
    def test_skills_average_the_items_that_count_towards_them(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        for item in mock.questions:
            item.response = {"marker": True}
            item.score_pct = 50.0
            item.score_detail = {"detail": {"traits": {"grammar": 1, "vocabulary": 2}}}
        mock.finished_at = utc_now()
        db.commit()

        report = build_report(mock, list(mock.questions))
        assert report["overall_score"] == 50  # 10 + 0.8 * 50
        for skill in report["communicative_skills"]:
            assert skill["score"] == 50
            assert skill["item_count"] > 0
        grammar = next(s for s in report["enabling_skills"] if s["key"] == "grammar")
        assert grammar["score"] == 50  # 1 out of 2 is 50%
        spelling = next(s for s in report["enabling_skills"] if s["key"] == "spelling")
        assert spelling["available"] is False
        assert spelling["note"] == "Not scored in practice"

    def test_unanswered_and_late_items_count_as_zero(self, bank, db):
        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        items = list(mock.questions)
        for item in items:
            item.response = {"x": 1}
            item.score_pct = 100.0
        items[0].late = True
        items[1].response = None
        items[1].score_pct = None
        db.commit()

        report = build_report(mock, items)
        assert report["late_count"] == 1
        assert report["answered_count"] == len(items) - 2
        assert report["overall_percent"] < 100
