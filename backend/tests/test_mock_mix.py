"""The question mix: a mock test must be the length and shape of a real one."""

import random
from collections import Counter

import pytest

from app.exam.blueprint import PARTS, PARTS_BY_SECTION, SPECS_BY_CODE, TOTAL_ITEM_WINDOW, counts_seconds
from app.exam.mix import BlueprintError, MAX_ATTEMPTS, allocate, build_mix, reading_seconds, validate_blueprint

SECTION_ORDER = ["speaking_writing", "reading", "listening"]
ALL_CODES = [spec.code for part in PARTS for spec in part.items]


@pytest.fixture(scope="module")
def mixes():
    rng = random.Random(4242)
    return [build_mix(rng) for _ in range(200)]


class TestTwoHundredMocks:
    def test_every_test_has_a_real_number_of_questions(self, mixes):
        for mix in mixes:
            assert TOTAL_ITEM_WINDOW[0] <= mix.item_count <= TOTAL_ITEM_WINDOW[1], mix.item_count

    def test_every_part_is_inside_its_published_windows(self, mixes):
        for mix in mixes:
            for part_spec, part_mix in zip(PARTS, mix.parts):
                low, high = part_spec.item_window
                assert low <= part_mix.item_count <= high, (part_spec.section, part_mix.item_count)
                minutes_low, minutes_high = part_spec.minutes_window
                assert minutes_low <= part_mix.minutes <= minutes_high, (part_spec.section, part_mix.minutes)

    def test_every_task_type_appears_at_least_once(self, mixes):
        for mix in mixes:
            counts = {code: n for part in mix.parts for code, n in part.counts.items()}
            assert len(counts) == 22
            assert all(n >= 1 for n in counts.values()), counts

    def test_no_task_type_goes_above_its_own_maximum(self, mixes):
        for mix in mixes:
            for part in mix.parts:
                for code, n in part.counts.items():
                    assert n <= SPECS_BY_CODE[code].count[1], (code, n)

    def test_questions_come_in_exam_order(self, mixes):
        for mix in mixes:
            items = mix.ordered_items()
            sections = [section for _, section in items]
            assert sections == sorted(sections, key=SECTION_ORDER.index)
            codes = [code for code, _ in items]
            assert codes == sorted(codes, key=ALL_CODES.index)

    def test_the_whole_test_runs_about_as_long_as_the_real_one(self, mixes):
        for mix in mixes:
            # The published parts add up to between 129 and 153 minutes.
            assert 125 <= mix.minutes <= 155, mix.minutes

    def test_reading_time_follows_the_number_of_reading_questions(self, mixes):
        for mix in mixes:
            reading = next(part for part in mix.parts if part.section == "reading")
            assert reading.seconds == reading_seconds(reading.item_count)

    def test_summary(self, mixes, capsys):
        """Prints the distribution so the mix can be eyeballed."""
        totals = Counter(mix.item_count for mix in mixes)
        per_type = Counter()
        per_part_items = {section: Counter() for section in SECTION_ORDER}
        per_part_minutes = {section: [] for section in SECTION_ORDER}
        for mix in mixes:
            for part in mix.parts:
                per_part_items[part.section][part.item_count] += 1
                per_part_minutes[part.section].append(part.minutes)
                per_type.update(part.counts)

        lines = ["", f"{len(mixes)} mock tests", "", "Questions per test:"]
        for total in sorted(totals):
            lines.append(f"  {total:>3}: {'#' * totals[total]} ({totals[total]})")
        lines.append("")
        lines.append(f"{'Part':<18}{'questions':>22}{'minutes':>16}")
        for section in SECTION_ORDER:
            counts = per_part_items[section]
            spread = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
            minutes = per_part_minutes[section]
            lines.append(f"  {section:<16}{spread:>22}{f'{min(minutes)}-{max(minutes)}':>16}")
        lines.append("")
        lines.append(f"{'Type':<8}{'per test: min':>14}{'mean':>8}{'max':>6}")
        for code in ALL_CODES:
            per_test = [part.counts.get(code, 0) for mix in mixes for part in mix.parts if code in part.counts]
            lines.append(
                f"  {code:<6}{min(per_test):>14}{sum(per_test) / len(per_test):>8.1f}{max(per_test):>6}"
                f"   (blueprint {SPECS_BY_CODE[code].count[0]}-{SPECS_BY_CODE[code].count[1]})"
            )
        with capsys.disabled():
            print("\n".join(lines))


class TestAllocation:
    def test_shares_a_total_across_the_parts_inside_their_windows(self):
        rng = random.Random(7)
        low = sum(part.item_window[0] for part in PARTS)
        high = min(TOTAL_ITEM_WINDOW[1], sum(part.item_window[1] for part in PARTS))
        for total in range(low, high + 1):
            allocation = allocate(total, rng)
            assert sum(allocation.values()) == total
            for part in PARTS:
                low, high = part.item_window
                assert low <= allocation[part.section] <= high

    def test_reading_clock_scales_with_questions_and_stays_in_its_window(self):
        assert reading_seconds(12) == 22 * 60  # clamped up to the published minimum
        assert reading_seconds(16) == 1600
        assert reading_seconds(18) == 30 * 60  # clamped down to the published maximum


class TestTheGuard:
    def test_the_real_blueprint_passes(self):
        validate_blueprint()

    def test_a_part_that_cannot_reach_its_window_is_refused(self, monkeypatch):
        from app.exam import blueprint as bp

        listening = PARTS_BY_SECTION["listening"]
        broken = tuple(
            part if part.section != "listening" else type(part)(**{**part.__dict__, "item_window": (40, 50)})
            for part in PARTS
        )
        monkeypatch.setattr(bp, "PARTS", broken)
        monkeypatch.setattr("app.exam.mix.PARTS", broken)
        with pytest.raises(BlueprintError) as error:
            validate_blueprint(samples=5)
        assert "listening" in str(error.value)
        assert listening is PARTS_BY_SECTION["listening"]  # the real blueprint is untouched
        assert listening.item_window[1] <= 20

    def test_an_impossible_total_is_refused(self, monkeypatch):
        monkeypatch.setattr("app.exam.mix.TOTAL_ITEM_WINDOW", (10, 20))
        with pytest.raises(BlueprintError) as error:
            validate_blueprint(samples=5)
        assert "doesn't overlap" in str(error.value)


class TestPartFitting:
    def test_a_part_is_trimmed_from_the_types_with_the_most(self):
        rng = random.Random(3)
        part = PARTS_BY_SECTION["speaking_writing"]
        from app.exam.mix import build_part

        mix = build_part(part, 30, rng)
        assert mix.item_count == 30
        # Repeat Sentence has the widest range, so it carries most of the trimming.
        assert mix.counts["RS"] <= SPECS_BY_CODE["RS"].count[1]
        assert all(count >= 1 for count in mix.counts.values())

    def test_a_part_never_stretches_its_clock_to_fit(self):
        rng = random.Random(11)
        from app.exam.mix import build_part

        for section in SECTION_ORDER:
            part = PARTS_BY_SECTION[section]
            for target in range(part.item_window[0], part.item_window[1] + 1):
                mix = build_part(part, target, rng)
                assert mix.item_count == target
                assert mix.seconds == counts_seconds(part, mix.counts)
                low, high = part.minutes_window
                assert low <= mix.minutes <= high, (section, target, mix.minutes)

    def test_fitting_gives_up_rather_than_looping_forever(self):
        assert MAX_ATTEMPTS <= 500
