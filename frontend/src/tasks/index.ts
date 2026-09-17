import type { TaskType } from "../api/types";
import type { TimerPhase } from "../hooks/useExamTimer";
import AnswerShortQuestion from "./AnswerShortQuestion";
import DescribeImage from "./DescribeImage";
import HighlightCorrectSummary from "./HighlightCorrectSummary";
import HighlightIncorrectWords from "./HighlightIncorrectWords";
import ListeningFillBlanks from "./ListeningFillBlanks";
import ListeningMultipleAnswers from "./ListeningMultipleAnswers";
import ListeningSingleAnswer from "./ListeningSingleAnswer";
import ReadAloud from "./ReadAloud";
import ReadingFillBlanks from "./ReadingFillBlanks";
import ReadingMultipleAnswers from "./ReadingMultipleAnswers";
import ReadingSingleAnswer from "./ReadingSingleAnswer";
import ReadingWritingFillBlanks from "./ReadingWritingFillBlanks";
import ReorderParagraphs from "./ReorderParagraphs";
import RepeatSentence from "./RepeatSentence";
import RespondToSituation from "./RespondToSituation";
import RetellLecture from "./RetellLecture";
import SelectMissingWord from "./SelectMissingWord";
import SummarizeGroupDiscussion from "./SummarizeGroupDiscussion";
import SummarizeSpokenText from "./SummarizeSpokenText";
import SummarizeWrittenText from "./SummarizeWrittenText";
import type { TaskComponent } from "./types";
import WriteEssay from "./WriteEssay";
import WriteFromDictation from "./WriteFromDictation";

export const TASKS: Record<string, TaskComponent> = {
  RA: ReadAloud,
  RS: RepeatSentence,
  DI: DescribeImage,
  RL: RetellLecture,
  ASQ: AnswerShortQuestion,
  SGD: SummarizeGroupDiscussion,
  RTS: RespondToSituation,
  SWT: SummarizeWrittenText,
  WE: WriteEssay,
  RWFIB: ReadingWritingFillBlanks,
  MCMA: ReadingMultipleAnswers,
  RO: ReorderParagraphs,
  RFIB: ReadingFillBlanks,
  MCSA: ReadingSingleAnswer,
  SST: SummarizeSpokenText,
  LMCMA: ListeningMultipleAnswers,
  LFIB: ListeningFillBlanks,
  HCS: HighlightCorrectSummary,
  LMCSA: ListeningSingleAnswer,
  SMW: SelectMissingWord,
  HIW: HighlightIncorrectWords,
  WFD: WriteFromDictation,
};

/** Typed writing tasks lock when time runs out but wait for the student to submit. Other untimed-out tasks submit automatically. */
export const WRITING_TYPES = new Set(["SWT", "WE", "SST"]);

/** The exam phases for a task type: optional audio lead-in and playback, preparation, then the answer time. */
export function phasesFor(type: TaskType): TimerPhase[] {
  const phases: TimerPhase[] = [];
  if (type.audio) {
    phases.push({ id: "leadin", label: "Audio starts in", seconds: 3 });
    phases.push({ id: "audio", label: "Listening", seconds: null });
  }
  if (type.prep_seconds > 0) {
    phases.push({ id: "prep", label: type.spoken ? "Recording starts in" : "Preparation", seconds: type.prep_seconds });
  }
  phases.push({ id: "answer", label: type.spoken ? "Recording" : "Time remaining", seconds: type.answer_seconds });
  return phases;
}
