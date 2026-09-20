"""Spelling: what counts as a mistake, what it costs, and what the report says about it."""

import pytest

from app.scoring import objective, spelling, writing
from app.scoring.aggregate import build_report
from app.spelling import dictionary
from app.spelling.checker import check, edit_distance, intended_word, near_miss
from app.spelling.variants import british_variants
from tests.test_mock_test import bank, make_user  # noqa: F401 - bank is a fixture


class TestTheDictionary:
    @pytest.mark.parametrize(
        "word",
        "colour organise centre defence behaviour realise labour metre programme analyse "
        "travelling licence catalogue aluminium grey tyre".split(),
    )
    def test_british_and_australian_spellings_are_accepted(self, word):
        assert dictionary.known(word), word

    @pytest.mark.parametrize(
        "word",
        "color organize center defense behavior realize labor meter program analyze "
        "traveling license catalog aluminum gray tire".split(),
    )
    def test_american_spellings_are_accepted_too(self, word):
        assert dictionary.known(word), word

    @pytest.mark.parametrize("word", "recieve seperate definately enviroment occured govenment untill".split())
    def test_real_misspellings_are_caught(self, word):
        assert not dictionary.known(word), word

    def test_capitalisation_does_not_matter(self):
        assert dictionary.known("Colour") and dictionary.known("COLOUR")

    def test_the_rules_do_not_invent_words(self):
        # "-or" to "-our" applies to colour, not to doctor.
        assert "doctour" not in british_variants("doctor")
        assert "watre" not in british_variants("water")
        assert "sence" not in british_variants("sense")
        assert "dogue" not in british_variants("dog")
        assert "sise" not in british_variants("size")
        assert british_variants("colour") == set()  # already British

    def test_the_dictionary_is_built_once(self):
        assert dictionary.size() > 150_000
        assert dictionary.size() == dictionary.size()


class TestNearMisses:
    def test_a_typo_is_a_misspelling_of_the_expected_word(self):
        assert near_miss("definately", "definitely")
        assert near_miss("comittee", "committee")

    def test_a_different_word_is_not_a_misspelling(self):
        assert not near_miss("however", "definitely")
        assert not near_miss("cost", "cat")

    def test_a_correct_word_is_not_a_misspelling_of_itself(self):
        assert not near_miss("committee", "committee")

    def test_short_words_allow_only_one_edit(self):
        assert near_miss("hosue", "house")  # five letters, two edits
        assert not near_miss("bat", "cot")  # three letters, two edits

    def test_edit_distance_stops_counting_past_the_cap(self):
        assert edit_distance("abc", "abc") == 0
        assert edit_distance("abc", "abd") == 1
        assert edit_distance("abc", "xyz", cap=2) == 3  # the cap plus one, not the true distance

    def test_the_closest_candidate_wins(self):
        assert intended_word("acheive", {"achieve", "achieved", "archive"}) == "achieve"
        assert intended_word("xylophone", {"achieve"}) is None


class TestCheckingTypedText:
    def test_counts_each_distinct_misspelling_once(self):
        result = check("The enviroment and the enviroment again")
        assert result.error_count == 1
        assert result.misspellings == [{"typed": "enviroment", "intended": "environment"}]

    def test_reports_the_rate_and_the_sample_size(self):
        result = check("one recieve two three four five six seven eight nine")
        assert result.typed_words == 10
        assert result.errors_per_hundred == 10.0

    def test_nothing_typed_has_no_rate_rather_than_a_perfect_one(self):
        assert check("").errors_per_hundred is None
        assert check(None).typed_words == 0

    def test_words_from_the_question_are_correct_by_definition(self):
        # A student copying a technical term out of the passage must not be marked wrong for it.
        assert check("Photosynthesis in thylakoids").error_count == 1
        assert check("Photosynthesis in thylakoids", "the thylakoids of a chloroplast").error_count == 0

    def test_numbers_are_not_spelling_mistakes(self):
        assert check("in 1987 there were 40000 people").error_count == 0


class TestWhatAMistakeCosts:
    GOOD = (
        "Urban density reduces transport emissions because residents travel shorter distances, and "
        "the research shows that compact neighbourhoods support public transport more effectively."
    )

    def test_clean_writing_scores_the_full_spelling_trait(self):
        result = writing.score_summarize_written_text(self.GOOD, ["urban density", "transport emissions"])
        assert result.detail["traits"]["spelling"] == 2
        assert result.detail["spelling"]["error_count"] == 0

    def test_a_badly_spelled_summary_loses_the_trait(self):
        bad = (
            "Urbn densty reduces transprt emmissions becuase residnts travl shortr distnces and the "
            "reserch shows compct neighbourhods suport publik transprt."
        )
        result = writing.score_summarize_written_text(bad, ["urban density", "transport emissions"])
        assert result.detail["traits"]["spelling"] == 0
        assert result.detail["spelling"]["error_count"] > 3

    def test_the_thresholds_come_from_settings(self, monkeypatch):
        from app.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("SPELLING_GOOD_PER_HUNDRED", "0.0")
        get_settings.cache_clear()
        try:
            assert spelling.trait(1.0) == 1  # would be 2 under the default threshold of 2.0
        finally:
            get_settings.cache_clear()

    def test_australian_spelling_is_never_penalised(self):
        australian = self.GOOD.replace("neighbourhoods", "neighbourhoods")
        american = self.GOOD.replace("neighbourhoods", "neighborhoods")
        key = ["urban density"]
        assert (
            writing.score_summarize_written_text(australian, key).detail["traits"]["spelling"]
            == writing.score_summarize_written_text(american, key).detail["traits"]["spelling"]
            == 2
        )


class TestDictation:
    SENTENCE = "The committee approved the environmental assessment last week"

    def test_a_misspelled_word_still_scores_zero_and_is_explained(self):
        result = objective.score_dictation(self.SENTENCE, "The comittee approved the environmental assessment last week")
        assert result.score == 7  # the misspelled word earns nothing
        assert result.max_score == 8
        assert result.detail["spelling"]["misspellings"] == [{"typed": "comittee", "intended": "committee"}]

    def test_a_perfect_answer_records_no_mistakes(self):
        result = objective.score_dictation(self.SENTENCE, self.SENTENCE)
        assert result.score == result.max_score
        assert result.detail["spelling"]["error_count"] == 0

    def test_a_word_the_student_never_heard_is_not_called_a_spelling_mistake(self):
        result = objective.score_dictation(self.SENTENCE, "The committee approved the enormous parrot last week")
        assert result.detail["spelling"]["misspellings"] == []

    def test_one_expected_word_is_only_blamed_once(self):
        result = objective.score_dictation("the committee met", "the comittee comitee met")
        assert len(result.detail["spelling"]["misspellings"]) == 1


class TestListeningBlanks:
    def test_a_typed_blank_that_is_a_near_miss_is_recorded(self):
        result = objective.score_blanks(["separate", "achieve"], ["seperate", "achieve"], typed=True)
        assert result.score == 1  # still wrong, exactly as in the real test
        assert result.detail["spelling"]["misspellings"] == [{"typed": "seperate", "intended": "separate"}]

    def test_reading_blanks_are_chosen_not_typed_so_spelling_is_not_checked(self):
        result = objective.score_blanks(["separate"], ["seperate"])
        assert "spelling" not in result.detail

    def test_a_wrong_word_is_not_a_spelling_mistake(self):
        result = objective.score_blanks(["separate"], ["combined"], typed=True)
        assert result.detail["spelling"]["misspellings"] == []


class TestTheSkillPercentage:
    def test_clean_spelling_scores_full_marks(self):
        assert spelling.skill_percent(0, 200) == 100.0

    def test_the_rate_is_what_counts_not_the_count(self):
        assert spelling.skill_percent(2, 100) == spelling.skill_percent(8, 400)

    def test_nothing_typed_gives_no_score_rather_than_zero(self):
        assert spelling.skill_percent(0, 0) is None

    def test_a_very_high_error_rate_floors_at_zero(self):
        assert spelling.skill_percent(50, 100) == 0.0


class TestTheReport:
    def test_spelling_is_scored_with_its_sample_size_and_the_words_to_learn(self, bank, db):
        from app.exam.assembler import assemble

        user = make_user(db)
        mock = assemble(db, user)
        db.commit()
        for item in mock.questions:
            item.response = {"text": "x"}
            item.score_pct = 50.0
            item.score_detail = {"traits": {"grammar": 1}}
        typed = mock.questions[0]
        typed.score_detail = {
            "traits": {"grammar": 1},
            "spelling": {
                "typed_words": 100,
                "error_count": 3,
                "errors_per_hundred": 3.0,
                "misspellings": [
                    {"typed": "recieve", "intended": "receive"},
                    {"typed": "seperate", "intended": "separate"},
                    {"typed": "enviroment", "intended": "environment"},
                ],
            },
        }
        db.flush()

        report = build_report(mock, list(mock.questions))
        skill = next(s for s in report["enabling_skills"] if s["key"] == "spelling")
        assert skill["available"] is True
        assert skill["detail"]["words_checked"] == 100
        assert skill["detail"]["error_count"] == 3
        assert skill["detail"]["errors_per_hundred"] == 3.0
        assert [m["typed"] for m in skill["detail"]["misspelled_words"]] == [
            "recieve", "seperate", "enviroment",
        ]
        assert [m["intended"] for m in skill["detail"]["misspelled_words"]] == [
            "receive", "separate", "environment",
        ]
        assert skill["note"] is None
