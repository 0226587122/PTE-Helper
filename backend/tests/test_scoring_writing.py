from app.scoring.writing import score_summarize_spoken_text, score_summarize_written_text, score_write_essay

SWT_KEYS = ["urban trees cool neighbourhoods", "trees reduce stormwater", "benefits unequal between suburbs"]


class TestSummarizeWrittenText:
    def test_good_single_sentence(self):
        text = (
            "Urban trees cool neighbourhoods and reduce stormwater, although their benefits are unequal because "
            "wealthier suburbs have more canopy than older industrial areas."
        )
        result = score_summarize_written_text(text, SWT_KEYS)
        assert result.zeroed_reason is None
        assert result.detail["traits"]["form"] == 1
        assert result.detail["traits"]["content"] == 2
        assert result.score >= 6

    def test_two_sentences_zero_everything(self):
        text = "Urban trees cool neighbourhoods. They also reduce stormwater in cities."
        result = score_summarize_written_text(text, SWT_KEYS)
        assert result.score == 0
        assert result.zeroed_reason

    def test_too_short_is_zero(self):
        assert score_summarize_written_text("Trees are good.", SWT_KEYS).score == 0

    def test_too_long_is_zero(self):
        text = " ".join(["trees"] * 76) + "."
        assert score_summarize_written_text(text, SWT_KEYS).score == 0

    def test_empty_is_zero(self):
        assert score_summarize_written_text(None, SWT_KEYS).score == 0


def essay(words: int, paragraphs: int = 4) -> str:
    sentence = "However, governments should invest in public transport because congestion harms productivity and health."
    per = sentence.split()
    body = []
    for _ in range(words // len(per)):
        body.append(sentence)
    text_words = " ".join(body).split()[:words]
    chunk = max(1, len(text_words) // paragraphs)
    parts = [" ".join(text_words[i : i + chunk]) for i in range(0, len(text_words), chunk)]
    return "\n\n".join(p[0].upper() + p[1:] + "." for p in parts)


class TestWriteEssay:
    keys = ["public transport investment", "congestion", "health"]

    def test_form_bands(self):
        assert score_write_essay(essay(250), self.keys).detail["traits"]["form"] == 2
        assert score_write_essay(essay(150), self.keys).detail["traits"]["form"] == 1
        assert score_write_essay(essay(350), self.keys).detail["traits"]["form"] == 1

    def test_under_120_words_is_zero(self):
        result = score_write_essay(essay(110), self.keys)
        assert result.score == 0
        assert result.zeroed_reason

    def test_over_380_words_is_zero(self):
        assert score_write_essay(essay(390), self.keys).score == 0

    def test_structure_counts_paragraphs(self):
        assert score_write_essay(essay(240, paragraphs=1), self.keys).detail["traits"]["structure"] == 0
        assert score_write_essay(essay(240, paragraphs=4), self.keys).detail["traits"]["structure"] == 2


class TestSummarizeSpokenText:
    keys = ["trees cool cities", "stormwater", "unequal canopy"]

    def test_in_range(self):
        text = " ".join(["Trees cool cities and slow stormwater while canopy is unequal."] * 6)
        result = score_summarize_spoken_text(text, self.keys)
        assert result.detail["traits"]["form"] == 2
        assert result.detail["traits"]["content"] == 2

    def test_under_40_is_zero(self):
        result = score_summarize_spoken_text("Trees cool cities.", self.keys)
        assert result.score == 0
        assert result.zeroed_reason

    def test_band_one_form(self):
        text = " ".join(["word"] * 45)
        assert score_summarize_spoken_text(text, self.keys).detail["traits"]["form"] == 1

    def test_over_100_is_zero(self):
        assert score_summarize_spoken_text(" ".join(["word"] * 101), self.keys).score == 0
