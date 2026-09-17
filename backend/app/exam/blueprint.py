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

# The reading part runs on one pooled clock, as in the real test, rather than per-item timing.
READING_SECTION_SECONDS = 30 * 60


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
    # A pooled clock for the whole part (reading), instead of a clock per item.
    section_seconds: int | None = None
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
        section_seconds=READING_SECTION_SECONDS,
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


def part_minutes(part: PartSpec) -> tuple[int, int]:
    """The shortest and longest this part can take, in whole minutes."""
    if part.section_seconds is not None:
        return (part.section_seconds // 60, part.section_seconds // 60)
    low = sum(spec.item_seconds() * spec.count[0] for spec in part.items)
    high = sum(spec.item_seconds() * spec.count[1] for spec in part.items)
    return (low // 60, high // 60)


def total_minutes() -> tuple[int, int]:
    low = sum(part_minutes(part)[0] for part in PARTS)
    high = sum(part_minutes(part)[1] for part in PARTS)
    return (low, high)


def item_count_range() -> tuple[int, int]:
    low = sum(spec.count[0] for part in PARTS for spec in part.items)
    high = sum(spec.count[1] for part in PARTS for spec in part.items)
    return (low, high)


def skills_for(code: str) -> tuple[str, ...]:
    return SPECS_BY_CODE[code].skills
