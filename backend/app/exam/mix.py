"""Decides how many questions of each task type a mock test contains.

The real test has 52 to 64 scored questions, and each part has its own published window for both
questions and minutes. So the mix is drawn from the top down:

1. Draw the total number of questions for the whole test.
2. Share that total across the three parts, inside each part's published window.
3. Inside a part, draw each task type in its own range, then trim the part down to its share by
   taking items from the types that have the most, never dropping a type below one item.
4. Keep the part's estimated length inside its published window. If a mix does not fit, draw again
   rather than stretching the clock, and keep the closest attempt as a fallback.

Drawing the total first is what keeps a mock test the length of a real one. Adding up each task
type's maximum instead would make every test longer and harsher than exam day, and would give the
types with wide ranges too much weight in the skill averages.
"""

import random
from dataclasses import dataclass

from app.exam.blueprint import PARTS, SPECS_BY_CODE, TOTAL_ITEM_WINDOW, PartSpec, counts_seconds, reading_seconds

# How many times to redraw a part before settling for the closest mix found.
MAX_ATTEMPTS = 200


@dataclass(frozen=True)
class PartMix:
    section: str
    counts: dict[str, int]
    seconds: int

    @property
    def item_count(self) -> int:
        return sum(self.counts.values())

    @property
    def minutes(self) -> int:
        return self.seconds // 60


@dataclass(frozen=True)
class MockMix:
    parts: tuple[PartMix, ...]

    @property
    def item_count(self) -> int:
        return sum(part.item_count for part in self.parts)

    @property
    def minutes(self) -> int:
        return sum(part.minutes for part in self.parts)

    def ordered_items(self) -> list[tuple[str, str]]:
        """(task type code, section) for every question, in the order students meet them."""
        items: list[tuple[str, str]] = []
        for part_spec, part_mix in zip(PARTS, self.parts):
            for spec in part_spec.items:
                items += [(spec.code, part_spec.section)] * part_mix.counts[spec.code]
        return items

    def pooled_seconds(self) -> dict[str, int]:
        """The clock for each part that runs on one clock for the whole part."""
        return {
            part_spec.section: part_mix.seconds
            for part_spec, part_mix in zip(PARTS, self.parts)
            if part_spec.pooled_clock
        }


def _feasible_total() -> tuple[int, int]:
    """The totals that can actually be shared across the parts, given each part's window."""
    low = max(TOTAL_ITEM_WINDOW[0], sum(part.item_window[0] for part in PARTS))
    high = min(TOTAL_ITEM_WINDOW[1], sum(part.item_window[1] for part in PARTS))
    return low, high


def allocate(total: int, rng: random.Random) -> dict[str, int]:
    """Share a total number of questions across the parts, inside each part's window."""
    allocation = {part.section: part.item_window[0] for part in PARTS}
    remaining = total - sum(allocation.values())
    room = [part for part in PARTS if allocation[part.section] < part.item_window[1]]
    while remaining > 0 and room:
        part = rng.choice(room)
        allocation[part.section] += 1
        remaining -= 1
        room = [p for p in PARTS if allocation[p.section] < p.item_window[1]]
    return allocation


def _trim_one(counts: dict[str, int], rng: random.Random) -> bool:
    """Take one question off the type that can best spare it. Returns False when nothing can give."""
    # First take from types sitting above their own range, starting with whichever is furthest above.
    above = {code: n - SPECS_BY_CODE[code].count[0] for code, n in counts.items() if n > SPECS_BY_CODE[code].count[0]}
    if above:
        most = max(above.values())
        counts[rng.choice([code for code, gap in above.items() if gap == most])] -= 1
        return True

    # Everything is already at its minimum, so the part is shorter than the task type ranges assume.
    # Spread the shortfall in proportion to how many questions each type normally has, rather than
    # taking it all from the widest type, which would distort the paper.
    share = {code: n / SPECS_BY_CODE[code].count[0] for code, n in counts.items() if n > 1}
    if not share:
        return False
    most = max(share.values())
    counts[rng.choice([code for code, value in share.items() if value == most])] -= 1
    return True


def _add_one(counts: dict[str, int], rng: random.Random) -> bool:
    """Add one question to the type that is furthest short of its normal share."""
    below = {
        code: n / SPECS_BY_CODE[code].count[0]
        for code, n in counts.items()
        if n < SPECS_BY_CODE[code].count[1]
    }
    if not below:
        return False
    fewest = min(below.values())
    counts[rng.choice([code for code, value in below.items() if value == fewest])] += 1
    return True


def _draw_counts(part: PartSpec, target: int, rng: random.Random) -> dict[str, int] | None:
    """Draw each task type in its range, then trim or pad the part to hit its share exactly."""
    counts = {spec.code: rng.randint(*spec.count) for spec in part.items}
    total = sum(counts.values())

    while total > target:
        if not _trim_one(counts, rng):
            return None
        total -= 1

    while total < target:
        if not _add_one(counts, rng):
            return None
        total += 1

    return counts


def _repair_time(part: PartSpec, counts: dict[str, int], rng: random.Random) -> dict[str, int]:
    """Swap a long task type for a short one (or the reverse) to bring a part inside its time window.

    The number of questions never changes, so the part keeps its share of the test. Only the balance
    between long and short task types moves.
    """
    low, high = part.minutes_window
    counts = dict(counts)
    for _ in range(len(part.items) * 4):
        minutes = counts_seconds(part, counts) / 60
        if low <= minutes <= high:
            break
        too_long = minutes > high
        # Give away an item from the longest type and take one for the shortest, or the reverse.
        givers = [c for c in counts if counts[c] > 1]  # never take a type out of the test
        takers = [c for c in counts if counts[c] < SPECS_BY_CODE[c].count[1]]
        if not givers or not takers:
            break
        by_length = lambda code: SPECS_BY_CODE[code].item_seconds()  # noqa: E731
        giver = max(givers, key=by_length) if too_long else min(givers, key=by_length)
        taker = min(takers, key=by_length) if too_long else max(takers, key=by_length)
        if giver == taker or by_length(giver) == by_length(taker):
            break
        counts[giver] -= 1
        counts[taker] += 1
    return counts


def build_part(part: PartSpec, target: int, rng: random.Random) -> PartMix:
    """A mix for one part: the right number of questions, and a length inside the published window."""
    low, high = part.minutes_window
    best: tuple[int, dict[str, int], int] | None = None  # (distance, counts, seconds)

    for _ in range(MAX_ATTEMPTS):
        counts = _draw_counts(part, target, rng)
        if counts is None:
            continue
        counts = _repair_time(part, counts, rng)
        seconds = counts_seconds(part, counts)
        minutes = seconds / 60
        if low <= minutes <= high:
            return PartMix(section=part.section, counts=counts, seconds=seconds)
        distance = int(min(abs(minutes - low), abs(minutes - high)) * 60)
        if best is None or distance < best[0]:
            best = (distance, counts, seconds)

    if best is None:  # pragma: no cover - only possible with a broken blueprint
        raise ValueError(f"No valid mix for {part.section} with {target} questions")
    return PartMix(section=part.section, counts=best[1], seconds=best[2])


def build_mix(rng: random.Random | None = None) -> MockMix:
    """Draw the whole mock test: total, then each part, then each task type."""
    rng = rng or random.Random()
    low, high = _feasible_total()
    total = rng.randint(low, high)
    allocation = allocate(total, rng)
    return MockMix(parts=tuple(build_part(part, allocation[part.section], rng) for part in PARTS))


class BlueprintError(ValueError):
    """The blueprint can't produce tests that match the published format."""


def validate_blueprint(samples: int = 50) -> None:
    """Check the blueprint can produce real-shaped tests. Run at startup so drift can't ship."""
    problems: list[str] = []

    low, high = _feasible_total()
    if low > high:
        problems.append(
            f"The parts can hold {sum(p.item_window[0] for p in PARTS)} to "
            f"{sum(p.item_window[1] for p in PARTS)} questions, which doesn't overlap the test total "
            f"{TOTAL_ITEM_WINDOW}."
        )

    for part in PARTS:
        type_low = sum(spec.count[0] for spec in part.items)
        type_high = sum(spec.count[1] for spec in part.items)
        if type_high < part.item_window[0]:
            problems.append(f"{part.section}: task types allow at most {type_high} questions, below its window {part.item_window}.")
        if len(part.items) > part.item_window[1]:
            problems.append(f"{part.section}: {len(part.items)} task types can't fit in {part.item_window[1]} questions.")
        if type_low > part.item_window[1] and len(part.items) > part.item_window[1]:
            problems.append(f"{part.section}: minimum counts total {type_low}, above its window {part.item_window}.")

    if not problems:
        rng = random.Random(20260920)
        for _ in range(samples):
            mix = build_mix(rng)
            if not TOTAL_ITEM_WINDOW[0] <= mix.item_count <= TOTAL_ITEM_WINDOW[1]:
                problems.append(f"A drawn test had {mix.item_count} questions, outside {TOTAL_ITEM_WINDOW}.")
                break
            for part_spec, part_mix in zip(PARTS, mix.parts):
                if not part_spec.item_window[0] <= part_mix.item_count <= part_spec.item_window[1]:
                    problems.append(
                        f"{part_spec.section}: drew {part_mix.item_count} questions, outside {part_spec.item_window}."
                    )
                if not part_spec.minutes_window[0] <= part_mix.minutes <= part_spec.minutes_window[1]:
                    problems.append(
                        f"{part_spec.section}: a drawn mix lasts {part_mix.minutes} minutes, outside "
                        f"{part_spec.minutes_window}."
                    )
                if any(count < 1 for count in part_mix.counts.values()):
                    problems.append(f"{part_spec.section}: a task type was left out of a test.")
            if problems:
                break

    if problems:
        raise BlueprintError(
            "The mock test blueprint doesn't match the published PTE Academic format:\n  - "
            + "\n  - ".join(dict.fromkeys(problems))
        )


__all__ = ["BlueprintError", "MockMix", "PartMix", "allocate", "build_mix", "reading_seconds", "validate_blueprint"]
