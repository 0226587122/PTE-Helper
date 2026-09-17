from app.scoring import estimated_score, score_answer
from app.scoring.objective import (
    score_blanks,
    score_dictation,
    score_incorrect_words,
    score_multiple_answers,
    score_reorder,
    score_single_answer,
)


class TestBlanks:
    def test_partial_credit_per_blank(self):
        result = score_blanks(["rising", "despite", "fund", "rural"], ["rising", "although", "fund", None])
        assert result.score == 2
        assert result.max_score == 4
        assert result.pct == 50.0
        assert result.detail["per_blank"] == [True, False, True, False]

    def test_case_and_spacing_ignored(self):
        assert score_blanks(["Carbon"], ["  carbon "]).score == 1

    def test_missing_answers_count_as_wrong(self):
        assert score_blanks(["a1", "b2"], None).score == 0

    def test_empty_string_is_not_a_match(self):
        assert score_blanks(["x"], [""]).score == 0


class TestMultipleAnswers:
    def test_plus_one_for_each_correct(self):
        assert score_multiple_answers([0, 2, 3], [0, 2]).score == 2

    def test_minus_one_for_each_wrong(self):
        result = score_multiple_answers([0, 2], [0, 2, 4])
        assert result.score == 1
        assert result.detail == {"correct_selected": 2, "incorrect_selected": 1}

    def test_never_below_zero(self):
        assert score_multiple_answers([0, 1], [2, 3, 4]).score == 0

    def test_selecting_everything_is_penalised(self):
        assert score_multiple_answers([1, 3], [0, 1, 2, 3, 4]).score == 0


def test_single_answer():
    assert score_single_answer(2, 2).score == 1
    assert score_single_answer(2, 1).score == 0
    assert score_single_answer(2, None).score == 0


class TestReorder:
    def test_perfect_order(self):
        result = score_reorder(["A", "B", "C", "D"], ["A", "B", "C", "D"])
        assert (result.score, result.max_score) == (3, 3)

    def test_adjacent_pairs_only(self):
        # B-C and C-D are correct neighbours, D-A is not.
        assert score_reorder(["A", "B", "C", "D"], ["B", "C", "D", "A"]).score == 2

    def test_reversed_scores_zero(self):
        assert score_reorder(["A", "B", "C", "D", "E"], ["E", "D", "C", "B", "A"]).score == 0

    def test_empty(self):
        assert score_reorder(["A", "B", "C"], []).score == 0


class TestIncorrectWords:
    def test_hits_and_wrong_clicks(self):
        result = score_incorrect_words([3, 10, 25], [3, 10, 11])
        assert result.score == 1
        assert result.max_score == 3

    def test_floor_at_zero(self):
        assert score_incorrect_words([3], [1, 2]).score == 0


class TestDictation:
    def test_counts_words_in_any_order(self):
        result = score_dictation("The library extends its opening hours during exams.", "during exams the library extends hours")
        assert result.score == 6
        assert result.max_score == 8

    def test_spelling_must_be_right(self):
        assert score_dictation("Research funding increased.", "Reserch funding increased").score == 2

    def test_repeated_words_counted_once_each(self):
        assert score_dictation("the cat saw the dog", "the the the the").score == 2

    def test_punctuation_and_case_ignored(self):
        assert score_dictation("Students, however, disagreed.", "students however disagreed").score == 3


def test_estimated_score_scale():
    assert estimated_score(0) == 10
    assert estimated_score(100) == 90
    assert estimated_score(50) == 50


def test_dispatch_ignores_bad_response_shapes():
    rendered = {"answer": {"correct": [0, 1]}}
    assert score_answer("MCMA", rendered, {"selected": "0,1"}).score == 0
    assert score_answer("MCMA", rendered, {"selected": [0, True, 1]}).score == 2
    assert score_answer("MCSA", {"answer": {"correct": 1}}, {"selected": "1"}).score == 0
