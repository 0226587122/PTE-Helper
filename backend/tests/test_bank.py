import copy
import json

import pytest

from app.bank import markup
from app.bank.files import DEFAULT_BANK_PATHS, load_bank
from app.bank.validation import validate_bank, validate_payload, validate_source
from app.scoring import score_answer
from app.scoring.text import words
from app.task_types import TYPES
from app.variants import SourceData, render
from tests.samples import LECTURE, PASSAGE_MARKUP, sample_bank

# Keys that would give an answer away if they appeared in what the browser gets before answering.
ANSWER_KEYS = {"answer", "answers", "correct", "blanks", "order", "incorrect", "originals", "accepted", "key_points", "sentence", "transcript"}


def _sources_by_key():
    sources, _ = sample_bank()
    return {s["source_key"]: s for s in sources}


def _source_data(key):
    if key is None:
        return None
    s = _sources_by_key()[key]
    return SourceData(s["source_key"], s["kind"], s["title"], s["body"], s.get("blank_markup"), s.get("turns"))


def _walk_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_keys(v)


class TestMarkup:
    def test_parse_and_fill(self):
        segments, blanks = markup.parse("A {{big|small|tall|wide}} dog and a {{red|blue|green|pink}} ball.")
        assert [b.correct for b in blanks] == ["big", "red"]
        assert segments == ["A ", 0, " dog and a ", 1, " ball."]
        assert markup.fill("A {{big|small}} dog.") == "A big dog."

    @pytest.mark.parametrize(
        "bad", ["A {{big|small dog.", "A {{big||small}} dog.", "A {{big|Big}} dog.", "A big} dog.", "A {{}} dog."]
    )
    def test_bad_markup(self, bad):
        with pytest.raises(markup.MarkupError):
            markup.parse(bad)


class TestValidation:
    def test_sample_bank_is_valid(self):
        sources, questions = sample_bank()
        report = validate_bank(sources, questions)
        assert report.errors == []
        assert all(report.counts[t.code] for t in TYPES)

    def test_counts_are_enforced(self):
        sources, questions = sample_bank()
        report = validate_bank(sources, questions, min_active=30, min_backup=15)
        assert any("RA: only 1 active" in e for e in report.errors)

    def test_passage_must_match_markup(self):
        sources, _ = sample_bank()
        passage = copy.deepcopy(sources[1])
        passage["body"] = passage["body"].replace("readily", "easily")
        assert any("exactly the body" in e for e in validate_source(passage))

    def test_lecture_length(self):
        assert any("110 to 150" in e for e in validate_source({"source_key": "x", "kind": "lecture", "title": "t", "body": "Too short."}))

    def test_answer_index_out_of_range(self):
        errors = validate_payload("MCSA", {"question": "Q?", "options": ["a", "b", "c", "d"], "answer": 4}, _sources_by_key()["pas-microplastics"])
        assert errors

    def test_multiple_answers_need_two(self):
        payload = {"question": "Q", "options": ["a", "b", "c", "d", "e"], "answers": [1]}
        assert validate_payload("MCMA", payload, _sources_by_key()["pas-microplastics"])

    def test_hiw_swap_must_be_in_lecture(self):
        payload = {"hiw_swaps": [["cooler", "warmer"], ["stormwater", "rain"], ["banana", "apple"], ["Melbourne", "Sydney"]]}
        assert any("banana" in e for e in validate_payload("HIW", payload, _sources_by_key()["lec-urban-trees"]))

    def test_smw_ending_must_match(self):
        payload = {"options": ["a private luxury", "essential public infrastructure", "x y", "z"], "answer": 0}
        assert any("must end with" in e for e in validate_payload("SMW", payload, _sources_by_key()["lec-urban-trees"]))

    def test_sentence_length(self):
        assert validate_payload("WFD", {"sentence": "Too short."}, None)

    def test_wrong_source_kind(self):
        assert validate_payload("RL", {"key_points": ["a", "b", "c"]}, _sources_by_key()["pas-microplastics"])

    def test_duplicates_detected(self):
        sources, questions = sample_bank()
        wfd = next(q for q in questions if q["type"] == "WFD")
        twin = copy.deepcopy(wfd)
        twin["payload"]["sentence"] = twin["payload"]["sentence"].upper()
        report = validate_bank(sources, questions + [twin])
        assert any("same text" in e for e in report.errors)


class TestRendering:
    @pytest.mark.parametrize("question", sample_bank()[1], ids=lambda q: q["type"])
    def test_display_never_contains_answers(self, question):
        rendered = render(question["type"], question["payload"], _source_data(question.get("source_key")), seed=42)
        leaked = ANSWER_KEYS & set(_walk_keys(rendered["display"]))
        assert not leaked, f"display leaks {leaked}"
        assert rendered["answer"]
        json.dumps(rendered)  # must be storable in a JSON column

    @pytest.mark.parametrize("question", sample_bank()[1], ids=lambda q: q["type"])
    def test_same_seed_same_variant(self, question):
        source = _source_data(question.get("source_key"))
        assert render(question["type"], question["payload"], source, 7) == render(question["type"], question["payload"], source, 7)

    @pytest.mark.parametrize("question", sample_bank()[1], ids=lambda q: q["type"])
    def test_perfect_answer_scores_full_marks_where_answer_is_known(self, question):
        code = question["type"]
        rendered = render(code, question["payload"], _source_data(question.get("source_key")), seed=3)
        a = rendered["answer"]
        perfect = {
            "RA": {"transcript": a.get("text")},
            "RS": {"transcript": a.get("sentence")},
            "WFD": {"text": a.get("sentence")},
            "RWFIB": {"answers": a.get("blanks")},
            "RFIB": {"answers": a.get("blanks")},
            "LFIB": {"answers": a.get("blanks")},
            "MCMA": {"selected": a.get("correct")},
            "LMCMA": {"selected": a.get("correct")},
            "MCSA": {"selected": a.get("correct")},
            "LMCSA": {"selected": a.get("correct")},
            "HCS": {"selected": a.get("correct")},
            "SMW": {"selected": a.get("correct")},
            "RO": {"order": a.get("order")},
            "HIW": {"selected": a.get("incorrect")},
        }
        if code not in perfect:
            pytest.skip("open response")
        assert score_answer(code, rendered, perfect[code]).pct == 100.0

    def test_describe_image_values_follow_template(self):
        payload = sample_bank()[1][2]["payload"]
        chart = render("DI", payload, None, 11)["display"]["chart"]
        assert chart["categories"] == payload["categories"]
        assert len(set(chart["values"])) == len(chart["values"])
        assert all(payload["min"] <= v <= payload["max"] for v in chart["values"])
        assert render("DI", payload, None, 12)["display"]["chart"]["values"] != chart["values"]

    def test_pie_chart_adds_to_100(self):
        payload = {"chart": "pie", "title": "Household energy use", "unit": "%", "categories": ["Heating", "Water", "Appliances", "Lighting"]}
        assert sum(render("DI", payload, None, 5)["display"]["chart"]["values"]) == 100

    def test_listening_blanks_rebuild_snippet(self):
        rendered = render("LFIB", {}, _source_data("lec-urban-trees"), 99)
        answers = rendered["answer"]["blanks"]
        text = "".join(s if isinstance(s, str) else answers[s["blank"]] for s in rendered["display"]["segments"])
        assert text == rendered["answer"]["transcript"]
        assert rendered["display"]["audio"] in LECTURE
        assert 4 <= len(answers) <= 6

    def test_incorrect_words_swaps_are_marked(self):
        rendered = render("HIW", sample_bank()[1][20]["payload"], _source_data("lec-urban-trees"), 5)
        tokens = rendered["display"]["tokens"]
        original_tokens = LECTURE.split()
        assert len(tokens) == len(original_tokens)
        changed = [i for i, (a, b) in enumerate(zip(tokens, original_tokens)) if a != b]
        assert changed == rendered["answer"]["incorrect"]
        assert 3 <= len(changed) <= 5

    def test_select_missing_word_audio_stops_before_answer(self):
        rendered = render("SMW", sample_bank()[1][19]["payload"], _source_data("lec-urban-trees"), 5)
        assert rendered["display"]["audio"].endswith("treated as")
        correct = rendered["display"]["options"][rendered["answer"]["correct"]]
        assert correct == "essential public infrastructure"

    def test_reorder_is_shuffled(self):
        rendered = render("RO", sample_bank()[1][11]["payload"], None, 1)
        assert [p["id"] for p in rendered["display"]["paragraphs"]] != rendered["answer"]["order"]

    def test_reorder_labels_do_not_reveal_the_order(self):
        payload = sample_bank()[1][11]["payload"]
        for seed in range(20):
            rendered = render("RO", payload, None, seed)
            shown = rendered["display"]["paragraphs"]
            # Labels always read A, B, C, D down the screen, whatever the shuffle.
            assert [p["id"] for p in shown] == ["A", "B", "C", "D"]
            by_id = {p["id"]: p["text"] for p in shown}
            assert [by_id[i] for i in rendered["answer"]["order"]] == payload["paragraphs"]

    def test_reading_blanks_options_include_correct(self):
        rendered = render("RWFIB", {}, _source_data("pas-microplastics"), 1)
        blanks = [s for s in rendered["display"]["segments"] if isinstance(s, dict)]
        for blank in blanks:
            assert rendered["answer"]["blanks"][blank["blank"]] in blank["options"]
        assert len(blanks) == len(markup.parse(PASSAGE_MARKUP)[1])

    def test_rfib_bank_has_extra_words(self):
        rendered = render("RFIB", {"extra_words": ["rarely", "cheapest", "allowed"]}, _source_data("pas-microplastics"), 1)
        assert len(rendered["display"]["bank"]) == 8
        assert "options" not in json.dumps(rendered["display"])


def test_repository_bank_meets_targets():
    """The real bank in seed/generated must pass validation with 30 active and 15 backup per type."""
    sources, questions, files = load_bank(DEFAULT_BANK_PATHS)
    if not questions:
        pytest.skip("No bank files yet.")
    report = validate_bank(sources, questions, min_active=30, min_backup=15)
    assert report.errors == []
    assert all(words(s["body"]) for s in sources)


def test_every_repository_question_renders_and_scores():
    """Render each real question with several seeds: no leaked answers, sensible variants, full marks for a perfect answer."""
    sources, questions, _ = load_bank(DEFAULT_BANK_PATHS)
    if not questions:
        pytest.skip("No bank files yet.")
    by_key = {
        s["source_key"]: SourceData(s["source_key"], s["kind"], s["title"], s["body"], s.get("blank_markup"), s.get("turns"))
        for s in sources
    }
    problems = []
    for i, q in enumerate(questions):
        code = q["type"]
        for seed in range(5):
            rendered = render(code, q["payload"], by_key.get(q.get("source_key")), seed)
            if ANSWER_KEYS & set(_walk_keys(rendered["display"])):
                problems.append(f"#{i} {code} leaks answers")
            a = rendered["answer"]
            if code == "HIW" and len(a["incorrect"]) < 3:
                problems.append(f"#{i} HIW only changed {len(a['incorrect'])} words (seed {seed})")
            if code == "LFIB" and len(a["blanks"]) < 4:
                problems.append(f"#{i} LFIB only {len(a['blanks'])} blanks (seed {seed})")
            perfect = {
                "WFD": {"text": a.get("sentence")}, "RWFIB": {"answers": a.get("blanks")}, "RFIB": {"answers": a.get("blanks")},
                "LFIB": {"answers": a.get("blanks")}, "MCMA": {"selected": a.get("correct")}, "LMCMA": {"selected": a.get("correct")},
                "MCSA": {"selected": a.get("correct")}, "LMCSA": {"selected": a.get("correct")}, "HCS": {"selected": a.get("correct")},
                "SMW": {"selected": a.get("correct")}, "RO": {"order": a.get("order")}, "HIW": {"selected": a.get("incorrect")},
            }
            if code in perfect and score_answer(code, rendered, perfect[code]).pct != 100.0:
                problems.append(f"#{i} {code} perfect answer did not score 100 (seed {seed})")
    assert problems == []
