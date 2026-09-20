"""Examiner-style feedback from Claude for speaking and writing answers."""

import json
import logging
from datetime import datetime, time
from typing import Any

import anthropic
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AIFeedback, SetQuestion, User, utc_now
from app.task_types import TYPES_BY_CODE

log = logging.getLogger(__name__)

EXAMINER_SYSTEM_PROMPT = """You are an experienced PTE Academic examiner helping a student practise.
You will get one practice task, the student's response and the automatic practice score.

Assess the response the way a PTE Academic examiner would, using the traits that apply to this task type:
- Speaking tasks: content, oral fluency and pronunciation. You only see a speech-to-text transcript, so judge
  fluency and pronunciation from what the transcript suggests (missing or garbled words, fillers, very short
  answers) and say plainly that a recording would be needed for a full pronunciation assessment.
- Summarize Written Text: content, form, grammar and vocabulary.
- Write Essay: content, form, development and structure, grammar, general linguistic range, vocabulary and spelling.
- Summarize Spoken Text: content, form, grammar, vocabulary and spelling.

Rules:
- `score` is your practice estimate on the 10 to 90 scale. It is not an official Pearson score.
- Give each trait a score, its maximum, and one or two sentences explaining it.
- Give two or three specific strengths and two or three specific, actionable improvements. Quote the student's
  own words where it helps.
- `model_answer` is a short, high-scoring answer to the same task, written in plain English at a natural length
  for the task (for Summarize Written Text this is one sentence; for Write Essay keep it to 200 to 300 words).
- Write for an international student: friendly, clear, and encouraging without hiding problems."""


class TraitScore(BaseModel):
    name: str
    score: float
    max: float
    comment: str


class ExaminerFeedback(BaseModel):
    score: int = Field(description="Practice estimate from 10 to 90")
    traits: list[TraitScore]
    strengths: list[str]
    improvements: list[str]
    model_answer: str


class FeedbackError(Exception):
    """A problem the student should see. Never uses a 5xx code, because hosting platforms
    replace 5xx responses with their own error page and the message would be lost."""

    def __init__(self, message: str, status_code: int = 424):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _task_material(code: str, display: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    material: dict[str, Any] = {}
    for key in ("text", "passage", "prompt", "situation", "chart"):
        if key in display:
            material[key] = display[key]
    if "turns" in display:
        material["discussion"] = display["turns"]
    elif "transcript" in answer:
        material["audio_transcript"] = answer["transcript"]
    elif code == "RS":
        material["sentence_heard"] = answer.get("sentence")
    if "key_points" in answer:
        material["key_points_expected"] = answer["key_points"]
    return material


def build_user_message(set_question: SetQuestion) -> str:
    code = set_question.practice_set.task_type_code
    definition = TYPES_BY_CODE[code]
    response = set_question.response or {}
    student_answer = response.get("transcript") if definition.spoken else response.get("text")
    body = {
        "task_type": definition.name,
        "instructions": definition.instructions,
        "task_material": _task_material(code, set_question.rendered_payload["display"], set_question.rendered_payload["answer"]),
        "student_response": student_answer or "",
        "response_is_speech_transcript": definition.spoken,
        "student_self_rating": response.get("self_rating"),
        "automatic_practice_score": {
            "percent": set_question.score_pct,
            "detail": set_question.score_detail,
        },
    }
    return "Please assess this practice response.\n\n" + json.dumps(body, ensure_ascii=False, indent=2)


def used_today(db: Session, user: User) -> int:
    midnight = datetime.combine(utc_now().date(), time.min)
    return db.scalar(
        select(func.count()).select_from(AIFeedback).where(AIFeedback.user_id == user.id, AIFeedback.created_at >= midnight)
    ) or 0


def get_or_create_feedback(db: Session, user: User, set_question: SetQuestion) -> AIFeedback:
    existing = db.scalars(select(AIFeedback).where(AIFeedback.set_question_id == set_question.id)).first()
    if existing:
        return existing

    settings = get_settings()
    code = set_question.practice_set.task_type_code
    if not TYPES_BY_CODE[code].ai_feedback:
        raise FeedbackError("Examiner feedback isn't available for this task type.", 400)
    if set_question.response is None:
        raise FeedbackError("Answer the question first, then ask for feedback.", 409)
    if used_today(db, user) >= settings.feedback_daily_limit:
        raise FeedbackError(
            f"You've used all {settings.feedback_daily_limit} examiner feedback requests for today. "
            "They reset at midnight UTC.",
            429,
        )
    if not settings.anthropic_api_key:
        raise FeedbackError("Examiner feedback isn't set up on this server yet.", 424)

    headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id} if settings.anthropic_workspace_id else None
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=120.0, default_headers=headers)
    try:
        message = client.messages.parse(
            model=settings.anthropic_model,
            max_tokens=16000,
            system=EXAMINER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(set_question)}],
            output_format=ExaminerFeedback,
        )
    except anthropic.RateLimitError:
        raise FeedbackError("The feedback service is busy right now. Please try again in a minute.") from None
    except anthropic.APIStatusError as exc:
        log.error("Anthropic API error %s: %s", exc.status_code, exc.message)
        raise FeedbackError("We couldn't get feedback right now. Please try again later.") from None
    except anthropic.APIConnectionError:
        log.exception("Could not reach the Anthropic API")
        raise FeedbackError("We couldn't reach the feedback service. Please try again later.") from None

    if message.stop_reason == "refusal" or message.parsed_output is None:
        log.warning("No parsed feedback (stop_reason=%s) for set question %s", message.stop_reason, set_question.id)
        raise FeedbackError("We couldn't produce feedback for this answer. Please try again.", 424)

    result = message.parsed_output
    feedback = AIFeedback(
        set_question_id=set_question.id,
        user_id=user.id,
        model=message.model,
        score=max(10, min(90, result.score)),
        traits=[t.model_dump() for t in result.traits],
        strengths=result.strengths,
        improvements=result.improvements,
        model_answer=result.model_answer,
    )
    db.add(feedback)
    db.commit()
    return feedback
