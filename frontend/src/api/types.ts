export type Section = "speaking_writing" | "reading" | "listening";

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: "student" | "admin";
  created_at: string;
}

export interface TaskType {
  code: string;
  name: string;
  section: Section;
  prep_seconds: number;
  answer_seconds: number;
  ai_feedback: boolean;
  tip: string;
  instructions: string;
  sort_order: number;
  audio: boolean;
  replay: boolean;
  spoken: boolean;
}

export interface SetQuestionSummary {
  position: number;
  set_question_id: number;
  answered: boolean;
  score_pct: number | null;
}

export interface PracticeSet {
  id: number;
  task_type: string;
  question_count: number;
  started_at: string;
  finished_at: string | null;
  average_pct: number | null;
  estimated_score: number | null;
  answered_count: number;
  questions: SetQuestionSummary[];
}

export interface ScoreResult {
  score: number;
  max_score: number;
  pct: number;
  detail: Record<string, unknown>;
  zeroed_reason: string | null;
}

export interface Trait {
  name: string;
  score: number;
  max: number;
  comment: string;
}

export interface Feedback {
  model: string;
  score: number;
  traits: Trait[];
  strengths: string[];
  improvements: string[];
  model_answer: string;
  created_at: string;
}

// What the browser receives for each task type before answering. Answers are never included.
export interface Turn {
  speaker: string;
  text: string;
}

export type BlankSegment = string | { blank: number; options?: string[] };

export interface ChartData {
  kind: "bar" | "line" | "pie";
  title: string;
  unit: string;
  x_label?: string | null;
  y_label?: string | null;
  categories: string[];
  values: number[];
}

export interface Display {
  text?: string;
  audio?: string;
  chart?: ChartData;
  turns?: Turn[];
  situation?: string;
  passage?: string;
  prompt?: string;
  question?: string;
  options?: string[];
  segments?: BlankSegment[];
  bank?: string[];
  paragraphs?: { id: string; text: string }[];
  tokens?: string[];
}

export interface Answer {
  text?: string;
  sentence?: string;
  key_points?: string[];
  transcript?: string | Turn[];
  accepted?: string[];
  notes?: string;
  blanks?: string[];
  passage?: string;
  correct?: number | number[];
  order?: string[];
  paragraphs?: { id: string; text: string }[];
  incorrect?: number[];
  originals?: Record<string, string>;
}

export interface SelfRating {
  content?: number;
  fluency?: number;
  pronunciation?: number;
  correct?: boolean;
}

export interface TaskResponse {
  transcript?: string;
  self_rating?: SelfRating;
  text?: string;
  answers?: (string | null)[];
  selected?: number | number[];
  order?: string[];
}

export interface Question {
  set_id: number;
  position: number;
  set_question_id: number;
  question_id: number;
  task_type: string;
  display: Display;
  answered: boolean;
  response: TaskResponse | null;
  result: ScoreResult | null;
  answer: Answer | null;
  feedback: Feedback | null;
}

export interface TypeProgress {
  code: string;
  sets_completed: number;
  best_score: number | null;
  last_score: number | null;
  last_practised: string | null;
}

export interface Progress {
  types: TypeProgress[];
  recent: {
    set_id: number;
    mode: "drill" | "mock";
    code: string | null;
    name: string;
    finished_at: string;
    average_pct: number;
    estimated_score: number;
  }[];
  overall_estimate: number | null;
  mock_tests_completed: number;
  best_mock_score: number | null;
  last_mock_score: number | null;
}

// Admin
export interface TypeSummary {
  code: string;
  name: string;
  active: number;
  backup: number;
  retired: number;
  open_reports: number;
}

export interface QuestionRow {
  id: number;
  task_type: string;
  status: "active" | "backup" | "retired";
  source_key: string | null;
  preview: string;
  difficulty: number | null;
  report_count: number;
  open_reports: number;
  times_served: number;
  created_at: string;
}

export interface QuestionPage {
  items: QuestionRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface Report {
  id: number;
  question_id: number;
  user_id: number;
  reason: string;
  created_at: string;
  resolved_at: string | null;
}

export interface QuestionDetail {
  id: number;
  task_type: string;
  status: "active" | "backup" | "retired";
  difficulty: number | null;
  payload: Record<string, unknown>;
  source: {
    id: number;
    source_key: string;
    kind: string;
    title: string;
    body: string;
    blank_markup: string | null;
    turns: Turn[] | null;
  } | null;
  report_count: number;
  times_served: number;
  created_at: string;
  promoted_at: string | null;
  retired_at: string | null;
  reports: Report[];
  promoted_ids: number[];
}

// --- Full mock test ---

export interface MockItemState {
  position: number;
  task_type: string;
  task_name: string;
  section: Section;
  answered: boolean;
  late: boolean;
}

export interface MockState {
  id: number;
  blueprint_version: string;
  status: "in_progress" | "finished";
  started_at: string;
  finished_at: string | null;
  question_count: number;
  current_position: number;
  answered_count: number;
  server_time: string;
  section_deadlines: Record<string, string>;
  items: MockItemState[];
}

export interface MockQuestion {
  set_id: number;
  position: number;
  set_question_id: number;
  question_id: number;
  task_type: string;
  section: Section;
  part_title: string;
  display: Display;
  answered: boolean;
  response: TaskResponse | null;
  prep_seconds: number;
  answer_seconds: number;
  deadline_at: string;
  seconds_remaining: number;
  section_deadline_at: string | null;
  section_seconds_remaining: number | null;
  allow_back: boolean;
  starts_part: boolean;
  server_time: string;
}

export interface MockAnswerAck {
  position: number;
  accepted: boolean;
  late: boolean;
  next_position: number | null;
  finished: boolean;
}

export interface BlueprintPart {
  section: Section;
  title: string;
  instructions: string;
  allow_back: boolean;
  minutes: { min: number; max: number };
  task_types: { code: string; name: string; count: number[]; skills: string[] }[];
}

export interface Blueprint {
  blueprint_version: string;
  minutes: { min: number; max: number };
  items: { min: number; max: number };
  personal_introduction: { title: string; prompt: string; prep_seconds: number; record_seconds: number };
  parts: BlueprintPart[];
}

export interface SkillScore {
  key: string;
  label: string;
  score: number | null;
  percent: number | null;
  item_count?: number;
  available?: boolean;
  note?: string | null;
}

export interface MockReport {
  set_id: number;
  blueprint_version: string;
  started_at: string | null;
  finished_at: string | null;
  overall_score: number;
  overall_percent: number;
  item_count: number;
  answered_count: number;
  late_count: number;
  communicative_skills: SkillScore[];
  enabling_skills: SkillScore[];
  sections: { section: Section; label: string; score: number | null; percent: number | null; item_count: number; answered_count: number }[];
  task_types: { code: string; percent: number | null; item_count: number }[];
  disclaimer: string;
}
