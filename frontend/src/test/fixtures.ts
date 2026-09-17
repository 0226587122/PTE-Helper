import type { Question, TaskType } from "../api/types";

export function taskType(overrides: Partial<TaskType> = {}): TaskType {
  return {
    code: "WFD",
    name: "Write from Dictation",
    section: "listening",
    prep_seconds: 0,
    answer_seconds: 60,
    ai_feedback: false,
    tip: "Write the first letter of each word.",
    instructions: "Type the sentence.",
    sort_order: 22,
    audio: true,
    replay: false,
    spoken: false,
    ...overrides,
  };
}

export function question(overrides: Partial<Question> = {}): Question {
  return {
    set_id: 1,
    position: 1,
    set_question_id: 10,
    question_id: 100,
    task_type: "WFD",
    display: {},
    answered: false,
    response: null,
    result: null,
    answer: null,
    feedback: null,
    ...overrides,
  };
}
