"""Turns a finished mock test into a score report.

This is an approximation of the way PTE Academic reports scores, for practice only. Pearson's
scoring is proprietary, so the numbers here will not match a real test. What is faithful:

* One item can count towards more than one communicative skill, as in the real integrated test. The
  mapping comes from the PTE Academic Score Guide and lives in exam/blueprint.py.
* A skill score is the average percentage of the items counting towards it, mapped onto the 10 to 90
  scale that PTE reports.
* Unanswered and late items count as zero, exactly like a missed item in the real test.

Spelling is not scored, because the app has no dictionary check. It is reported as unavailable
rather than as a zero, so a student is not misled.
"""

from typing import Any

from app.exam.blueprint import LISTENING, READING, SPEAKING, WRITING, skills_for
from app.models import PracticeSet, SetQuestion
from app.scoring.result import estimated_score

COMMUNICATIVE_SKILLS = (LISTENING, READING, SPEAKING, WRITING)

SKILL_LABELS = {
    LISTENING: "Listening",
    READING: "Reading",
    SPEAKING: "Speaking",
    WRITING: "Writing",
}

SECTION_LABELS = {
    "speaking_writing": "Speaking and Writing",
    "reading": "Reading",
    "listening": "Listening",
}

# Enabling skills, and where each one comes from in the per-item score details.
# (trait name, the maximum that trait is scored out of, which item traits to read it from)
ENABLING_SKILLS: dict[str, tuple[str, str]] = {
    "grammar": ("Grammar", "writing"),
    "oral_fluency": ("Oral fluency", "speaking"),
    "pronunciation": ("Pronunciation", "speaking"),
    "vocabulary": ("Vocabulary", "writing"),
    "written_discourse": ("Written discourse", "writing"),
    "spelling": ("Spelling", "unavailable"),
}

# Writing traits are scored out of small whole numbers; convert them to percentages.
WRITING_TRAIT_MAX = {"grammar": 2, "vocabulary": 2, "structure": 2, "linguistic_range": 2, "content": 3, "form": 2}


def item_percent(item: SetQuestion) -> float:
    """An item's score as a percentage. Unanswered or late items count as zero."""
    if item.response is None or item.late or item.score_pct is None:
        return 0.0
    return float(item.score_pct)


def _traits(item: SetQuestion) -> dict[str, Any]:
    detail = item.score_detail or {}
    inner = detail.get("detail") if isinstance(detail.get("detail"), dict) else detail
    traits = inner.get("traits") if isinstance(inner, dict) else None
    return traits if isinstance(traits, dict) else {}


def _enabling_percentages(items: list[SetQuestion]) -> dict[str, list[float]]:
    """Collect percentages for each enabling skill from the item score details."""
    collected: dict[str, list[float]] = {key: [] for key in ENABLING_SKILLS}
    for item in items:
        traits = _traits(item)
        if not traits:
            continue
        late = item.late or item.response is None
        if "fluency" in traits or "pronunciation" in traits:
            # Speaking traits are already percentages.
            if "fluency" in traits:
                collected["oral_fluency"].append(0.0 if late else float(traits["fluency"]))
            if "pronunciation" in traits:
                collected["pronunciation"].append(0.0 if late else float(traits["pronunciation"]))
            continue
        for trait, values in (("grammar", "grammar"), ("vocabulary", "vocabulary")):
            if trait in traits:
                top = WRITING_TRAIT_MAX[trait]
                collected[values].append(0.0 if late else float(traits[trait]) / top * 100)
        discourse = [traits[name] / WRITING_TRAIT_MAX[name] * 100 for name in ("structure", "linguistic_range") if name in traits]
        if discourse:
            collected["written_discourse"].append(0.0 if late else sum(discourse) / len(discourse))
    return collected


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def build_report(practice_set: PracticeSet, items: list[SetQuestion]) -> dict[str, Any]:
    """The full score report for a finished mock test."""
    percentages = {item.position: item_percent(item) for item in items}
    overall_pct = _average(list(percentages.values())) or 0.0

    communicative: list[dict[str, Any]] = []
    for skill in COMMUNICATIVE_SKILLS:
        values = [percentages[item.position] for item in items if skill in skills_for(item.task_type_code or "")]
        average = _average(values)
        communicative.append(
            {
                "key": skill,
                "label": SKILL_LABELS[skill],
                "score": estimated_score(average) if average is not None else None,
                "percent": average,
                "item_count": len(values),
            }
        )

    collected = _enabling_percentages(items)
    enabling = []
    for key, (label, source) in ENABLING_SKILLS.items():
        average = _average(collected[key])
        enabling.append(
            {
                "key": key,
                "label": label,
                "score": estimated_score(average) if average is not None else None,
                "percent": average,
                "available": average is not None,
                "note": "Not scored in practice" if source == "unavailable" else None,
            }
        )

    sections = []
    for section, label in SECTION_LABELS.items():
        section_items = [item for item in items if item.section == section]
        if not section_items:
            continue
        answered = [item for item in section_items if item.response is not None and not item.late]
        average = _average([percentages[item.position] for item in section_items])
        sections.append(
            {
                "section": section,
                "label": label,
                "score": estimated_score(average) if average is not None else None,
                "percent": average,
                "item_count": len(section_items),
                "answered_count": len(answered),
            }
        )

    by_type: dict[str, list[float]] = {}
    for item in items:
        by_type.setdefault(item.task_type_code or "", []).append(percentages[item.position])

    return {
        "set_id": practice_set.id,
        "blueprint_version": practice_set.blueprint_version,
        "started_at": practice_set.started_at.isoformat() if practice_set.started_at else None,
        "finished_at": practice_set.finished_at.isoformat() if practice_set.finished_at else None,
        "overall_score": estimated_score(overall_pct),
        "overall_percent": overall_pct,
        "item_count": len(items),
        "answered_count": sum(1 for item in items if item.response is not None and not item.late),
        "late_count": sum(1 for item in items if item.late),
        "communicative_skills": communicative,
        "enabling_skills": enabling,
        "sections": sections,
        "task_types": [
            {"code": code, "percent": _average(values), "item_count": len(values)} for code, values in by_type.items()
        ],
        "disclaimer": (
            "These scores are a practice estimate produced by this app, not official Pearson PTE Academic "
            "results. Use them to see where to focus, not to predict your exam score."
        ),
    }
