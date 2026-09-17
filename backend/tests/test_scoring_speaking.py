from app.scoring.speaking import (
    score_describe_image,
    score_read_aloud,
    score_repeat_sentence,
    score_retell_lecture,
    score_short_answer,
)

TEXT = "Coral reefs cover less than one percent of the ocean floor but support a quarter of marine species."


class TestReadAloud:
    def test_perfect_transcript(self):
        result = score_read_aloud(TEXT, {"transcript": TEXT})
        assert result.pct == 100.0

    def test_missing_words_reduce_content(self):
        result = score_read_aloud(TEXT, {"transcript": "Coral reefs cover less than one percent of the ocean floor"})
        assert 40 < result.pct < 80
        assert result.detail["words_matched"] == 11

    def test_self_rating_sets_delivery(self):
        result = score_read_aloud(TEXT, {"transcript": TEXT, "self_rating": {"fluency": 2, "pronunciation": 3}})
        assert result.detail["traits"] == {"content": 100, "fluency": 40, "pronunciation": 60}
        # 0.4 * 100% content + 0.3 * 40% fluency + 0.3 * 60% pronunciation
        assert result.pct == 70.0

    def test_no_answer_scores_zero(self):
        result = score_read_aloud(TEXT, {"transcript": ""})
        assert result.score == 0
        assert result.zeroed_reason

    def test_self_rating_only_when_no_speech_recognition(self):
        result = score_read_aloud(TEXT, {"self_rating": {"content": 4, "fluency": 4, "pronunciation": 4}})
        assert result.pct == 80.0


class TestRepeatSentence:
    sentence = "The seminar has been moved to the main lecture theatre."

    def test_all_words_band_three(self):
        assert score_repeat_sentence(self.sentence, {"transcript": self.sentence}).detail["content_band"] == 3

    def test_half_words_band_two(self):
        result = score_repeat_sentence(self.sentence, {"transcript": "the seminar has been moved to"})
        assert result.detail["content_band"] == 2

    def test_few_words_band_one(self):
        assert score_repeat_sentence(self.sentence, {"transcript": "the lecture"}).detail["content_band"] == 1

    def test_unrelated_words_band_zero(self):
        assert score_repeat_sentence(self.sentence, {"transcript": "banana orange"}).detail["content_band"] == 0


class TestOpenResponses:
    keys = ["urban trees cool neighbourhoods", "stormwater", "benefits unequal"]

    def test_key_points_drive_content(self):
        transcript = (
            "The lecture was about how urban trees cool neighbourhoods and slow stormwater, but the benefits are "
            "unequal across the city."
        )
        result = score_retell_lecture(self.keys, {"transcript": transcript})
        assert result.detail["key_points_covered"] == [True, True, True]
        assert result.detail["traits"]["content"] == 100

    def test_very_short_answer_zeroed(self):
        result = score_retell_lecture(self.keys, {"transcript": "trees are nice"})
        assert result.score == 0
        assert "short" in result.zeroed_reason

    def test_describe_image(self):
        transcript = "This bar chart shows rainfall by city. Wellington has the highest and Perth has the lowest amount."
        result = score_describe_image(["Rainfall by city", "Wellington highest", "Perth lowest"], {"transcript": transcript})
        assert result.detail["key_points_covered"] == [True, True, True]


class TestShortAnswer:
    def test_accepted_answer_in_transcript(self):
        assert score_short_answer(["thermometer"], {"transcript": "a thermometer"}).score == 1

    def test_multi_word_answer(self):
        assert score_short_answer(["solar system"], {"transcript": "it is the solar system"}).score == 1

    def test_wrong(self):
        assert score_short_answer(["thermometer"], {"transcript": "barometer"}).score == 0

    def test_self_rating_fallback(self):
        assert score_short_answer(["thermometer"], {"self_rating": {"correct": True}}).score == 1
