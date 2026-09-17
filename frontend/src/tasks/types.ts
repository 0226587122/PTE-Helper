import type { ComponentType } from "react";

import type { Question, TaskResponse, TaskType } from "../api/types";
import type { Recorder } from "../hooks/useRecorder";

export type Stage = "leadin" | "audio" | "prep" | "answer" | "done";

export interface TaskProps {
  type: TaskType;
  question: Question;
  response: TaskResponse;
  onChange: (next: TaskResponse) => void;
  /** No more changes allowed: time is up or the answer has been submitted. */
  locked: boolean;
  /** The question has been answered and marked, so show the correct answers. */
  review: boolean;
  stage: Stage;
  speaking: boolean;
  recorder?: Recorder;
}

export type TaskComponent = ComponentType<TaskProps>;
