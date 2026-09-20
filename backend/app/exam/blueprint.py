"""The full mock test blueprint: the single source of truth for a mock test's shape.

Everything about a mock test comes from here: which task types appear, in what order, how many
items of each, how long each item allows, and which communicative skills an item counts towards.
Nothing here is hard coded anywhere else.

The item counts and timings follow the published PTE Academic test format, and the skills each task
type counts towards follow the PTE Academic Score Guide. Timings for individual items come from the
task type definitions in app/task_types.py so drills and mock tests always agree.

Check https://www.pearsonpte.com/pte-academic/test-format before each release in case Pearson
changes the format, and raise BLUEPRINT_VERSION when this file changes.
"""

from dataclasses import dataclass

from app.task_types import TYPES_BY_CODE

BLUEPRINT_VERSION = "2025.08-mock-1"

LISTENING = "listening"
READING = "reading"
SPEAKING = "speaking"
WRITING = "writing"

# Extra seconds allowed on top of an item's own timing before an answer counts as late. It covers
# the audio lead-in, the student pressing Next, and normal network delay.
ITEM_GRACE_SECONDS = 20

# Moving between questions costs time in the real test too: instructions, loading and the student
# pressing Next. Counted per item when estimating how long a part takes.
TRANSITION_SECONDS = 8

# How many scored questions a real test has in total. Pearson's Test Taker and Institution Score
# Guides both say 65 to 75 questions across the 22 task types. The mix is drawn to fit this, rather
# than being whatever the task type ranges happen to add up to.
TOTAL_ITEM_WINDOW = (65, 75)

# The reading part runs on one pooled clock. Its length follows the number of questions drawn,
# then is clamped to the published window for the part.
READING_SECONDS_PER_ITEM = 100


@dataclass(frozen=True)
class ItemSpec:
    """One task type's place in a mock test."""

    code: str
    count: tuple[int, int]
    skills: tuple[str, ...]
    # Typical length of this type's recording, used only to estimate how long a part takes.
    # The app reads its audio aloud from the question text, so the real length varies a little.
    audio_seconds: int = 0

    @property
    def name(self) -> str:
        return TYPES_BY_CODE[self.code].name

    @property
    def section(self) -> str:
        return TYPES_BY_CODE[self.code].section

    @property
    def prep_seconds(self) -> int:
        return TYPES_BY_CODE[self.code].prep_seconds

    @property
    def answer_seconds(self) -> int:
        return TYPES_BY_CODE[self.code].answer_seconds

    def item_seconds(self) -> int:
        """How long one item takes: audio, preparation and answering."""
        definition = TYPES_BY_CODE[self.code]
        return self.audio_seconds + definition.prep_seconds + definition.answer_seconds


@dataclass(frozen=True)
class PartSpec:
    """One part of the exam, in the order students meet it."""

    section: str
    title: str
    instructions: str
    items: tuple[ItemSpec, ...]
    # How many questions this part may contain, from the published test format.
    item_window: tuple[int, int] = (1, 99)
    # How many minutes this part may take, from the published test format.
    minutes_window: tuple[int, int] = (1, 999)
    # True when the part runs on one clock for the whole part (reading) instead of a clock per item.
    pooled_clock: bool = False
    # Students may move back and change answers inside this part.
    allow_back: bool = False


PARTS: tuple[PartSpec, ...] = (
    PartSpec(
        section="speaking_writing",
        title="Part 1: Speaking and Writing",
        instructions=(
            "You will speak into your microphone and type two written answers. Each question has its own "
            "timing, shown at the top of the screen. You cannot go back to a question once you have moved on."
        ),
        items=(
            ItemSpec("RA", (6, 7), (SPEAKING,)),
            ItemSpec("RS", (10, 12), (LISTENING, SPEAKING), audio_seconds=6),
            ItemSpec("DI", (5, 6), (SPEAKING,)),
            ItemSpec("RL", (2, 3), (LISTENING, SPEAKING), audio_seconds=90),
            ItemSpec("ASQ", (5, 6), (LISTENING,), audio_seconds=6),
            ItemSpec("SGD", (2, 3), (LISTENING, SPEAKING), audio_seconds=120),
            ItemSpec("RTS", (2, 3), (SPEAKING,), audio_seconds=12),
            ItemSpec("SWT", (2, 2), (READING, WRITING)),
            ItemSpec("WE", (1, 1), (WRITING,)),
        ),
        # The task type ranges published in the score guide add up to at least 33 questions once a
        # part has to fill 76 minutes, so the bottom of this window is higher than the headline
        # "30 questions" figure.
        item_window=(35, 41),
        minutes_window=(76, 84),
    ),
    PartSpec(
        section="reading",
        title="Part 2: Reading",
        instructions=(
            "The clock runs for the whole part rather than for each question. You may use Previous and Next "
            "to go back and change your answers while time remains."
        ),
        items=(
            ItemSpec("RWFIB", (5, 6), (READING, WRITING)),
            ItemSpec("MCMA", (2, 3), (READING,)),
            ItemSpec("RO", (2, 3), (READING,)),
            ItemSpec("RFIB", (4, 5), (READING,)),
            ItemSpec("MCSA", (2, 3), (READING,)),
        ),
        item_window=(15, 20),
        minutes_window=(22, 30),
        pooled_clock=True,
        allow_back=True,
    ),
    PartSpec(
        section="listening",
        title="Part 3: Listening",
        instructions=(
            "Each recording plays once only and cannot be replayed. Summarize Spoken Text has its own "
            "10 minute clock. You cannot go back to a question once you have moved on."
        ),
        items=(
            ItemSpec("SST", (1, 1), (LISTENING, WRITING), audio_seconds=75),
            ItemSpec("LMCMA", (2, 3), (LISTENING,), audio_seconds=65),
            ItemSpec("LFIB", (2, 3), (LISTENING,), audio_seconds=45),
            ItemSpec("HCS", (2, 3), (LISTENING, READING), audio_seconds=60),
            ItemSpec("LMCSA", (2, 3), (LISTENING,), audio_seconds=45),
            ItemSpec("SMW", (1, 2), (LISTENING,), audio_seconds=45),
            ItemSpec("HIW", (2, 3), (LISTENING, READING), audio_seconds=30),
            ItemSpec("WFD", (3, 4), (LISTENING, WRITING), audio_seconds=6),
        ),
        # Summarize Spoken Text alone takes ten minutes, so this part cannot hold as many questions
        # as the other two and still finish inside its published window.
        item_window=(15, 15),
        minutes_window=(31, 39),
    ),
)

PARTS_BY_SECTION = {part.section: part for part in PARTS}
SPECS_BY_CODE = {spec.code: spec for part in PARTS for spec in part.items}

# A short spoken introduction opens the real test. It is not scored and no question bank is needed,
# so the runner shows it as a fixed step before Part 1.
PERSONAL_INTRODUCTION = {
    "title": "Personal introduction",
    "prompt": (
        "Read the prompt below. In 25 seconds, you must reply in your own words, as naturally and clearly as "
        "possible. You have 30 seconds to record your response. Your response will not be scored.\n\n"
        "Please introduce yourself. For example, you could talk about one or more of the following:\n"
        "  • your interests\n  • your plans for future study\n  • why you want to study abroad\n"
        "  • why you need to learn English\n  • why you chose this test"
    ),
    "prep_seconds": 25,
    "record_seconds": 30,
}


def reading_seconds(item_count: int) -> int:
    """The pooled reading clock for a test with this many reading questions."""
    part = PARTS_BY_SECTION["reading"]
    low, high = part.minutes_window
    return max(low * 60, min(high * 60, item_count * READING_SECONDS_PER_ITEM))


def counts_seconds(part: PartSpec, counts: dict[str, int]) -> int:
    """How long a part takes with this mix of questions, including moving between them."""
    if part.pooled_clock:
        return reading_seconds(sum(counts.values()))
    spec_seconds = sum(SPECS_BY_CODE[code].item_seconds() * n for code, n in counts.items())
    return spec_seconds + TRANSITION_SECONDS * sum(counts.values())


def part_minutes(part: PartSpec) -> tuple[int, int]:
    """The published length of this part, in whole minutes."""
    return part.minutes_window


def total_minutes() -> tuple[int, int]:
    low = sum(part.minutes_window[0] for part in PARTS)
    high = sum(part.minutes_window[1] for part in PARTS)
    return (low, high)


def item_count_range() -> tuple[int, int]:
    """How many questions a mock test has, which is drawn first and then shared across the parts."""
    return TOTAL_ITEM_WINDOW


def skills_for(code: str) -> tuple[str, ...]:
    return SPECS_BY_CODE[code].skills
