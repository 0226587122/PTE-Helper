"""Server-side timing for a mock test.

The browser shows a countdown, but the server decides. Every deadline is stored when an item or a
part is first served, so a refresh, a new tab or a slow network can't buy extra time.
"""

from datetime import datetime, timedelta

from app.config import get_settings
from app.exam.blueprint import ITEM_GRACE_SECONDS, PARTS_BY_SECTION
from app.models import PracticeSet, SetQuestion, utc_now
from app.task_types import TYPES_BY_CODE


def scaled(seconds: float) -> int:
    """Apply MOCK_TIME_SCALE, which end-to-end tests use to run a mock test quickly."""
    return max(1, round(seconds * get_settings().mock_time_scale))


def item_allowance(code: str) -> int:
    """Seconds a single item allows, including preparation and a small grace period."""
    definition = TYPES_BY_CODE[code]
    return scaled(definition.prep_seconds + definition.answer_seconds + ITEM_GRACE_SECONDS)


def section_deadline(practice_set: PracticeSet, section: str) -> datetime | None:
    raw = (practice_set.section_deadlines or {}).get(section)
    return datetime.fromisoformat(raw) if raw else None


def start_section(practice_set: PracticeSet, section: str, now: datetime | None = None) -> datetime | None:
    """Start a part's pooled clock the first time the student reaches it (reading only)."""
    part = PARTS_BY_SECTION.get(section)
    if part is None or not part.pooled_clock:
        return None
    existing = section_deadline(practice_set, section)
    if existing:
        return existing
    # The length was drawn with the mix; fall back to the published maximum for older attempts.
    seconds = (practice_set.section_seconds or {}).get(section) or part.minutes_window[1] * 60
    deadline = (now or utc_now()) + timedelta(seconds=scaled(seconds))
    deadlines = dict(practice_set.section_deadlines or {})
    deadlines[section] = deadline.isoformat()
    practice_set.section_deadlines = deadlines
    return deadline


def serve(practice_set: PracticeSet, item: SetQuestion, now: datetime | None = None) -> datetime:
    """Record that an item was shown and work out when its answer is due."""
    now = now or utc_now()
    pooled = start_section(practice_set, item.section or "", now)
    if item.served_at is None:
        item.served_at = now
    if item.deadline_at is None:
        item.deadline_at = pooled or (item.served_at + timedelta(seconds=item_allowance(item.task_type_code or "")))
    elif pooled:
        # Every reading item shares the part's clock.
        item.deadline_at = pooled
    return item.deadline_at


def remaining_seconds(deadline: datetime | None, now: datetime | None = None) -> int | None:
    if deadline is None:
        return None
    return max(0, int((deadline - (now or utc_now())).total_seconds()))


def is_late(item: SetQuestion, now: datetime | None = None) -> bool:
    return item.deadline_at is not None and (now or utc_now()) > item.deadline_at
