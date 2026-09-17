import { useCallback, useEffect, useRef, useState } from "react";

export type PhaseId = "leadin" | "audio" | "prep" | "answer";

export interface TimerPhase {
  id: PhaseId;
  label: string;
  /** Length in seconds, or null for a phase that ends only when advance() is called (such as audio playback). */
  seconds: number | null;
}

export interface ExamTimer {
  phase: TimerPhase | null;
  phaseIndex: number;
  remaining: number | null;
  done: boolean;
  running: boolean;
  advance: () => void;
  finish: () => void;
  start: () => void;
}

interface Options {
  autoStart?: boolean;
  onPhaseStart?: (phase: TimerPhase) => void;
  onComplete?: () => void;
}

/**
 * Runs a sequence of exam phases (audio lead-in, audio, preparation, answer), counting down each timed phase
 * and moving to the next automatically. Works from wall-clock deadlines so it stays accurate if the tab is busy.
 */
export function useExamTimer(phases: TimerPhase[], { autoStart = true, onPhaseStart, onComplete }: Options = {}): ExamTimer {
  const [running, setRunning] = useState(autoStart);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [remaining, setRemaining] = useState<number | null>(phases[0]?.seconds ?? null);
  const callbacks = useRef({ onPhaseStart, onComplete });
  callbacks.current = { onPhaseStart, onComplete };

  const done = phaseIndex >= phases.length;
  const phase = done ? null : phases[phaseIndex];

  const advance = useCallback(() => {
    setPhaseIndex((index) => Math.min(index + 1, phases.length));
  }, [phases.length]);

  const finish = useCallback(() => setPhaseIndex(phases.length), [phases.length]);
  const start = useCallback(() => setRunning(true), []);

  // Announce each phase as it begins, and completion at the end.
  useEffect(() => {
    if (!running) return;
    if (done) {
      callbacks.current.onComplete?.();
      return;
    }
    callbacks.current.onPhaseStart?.(phases[phaseIndex]);
  }, [phaseIndex, running, done]);

  // Count down timed phases.
  useEffect(() => {
    if (!running || done) return;
    const seconds = phases[phaseIndex].seconds;
    setRemaining(seconds);
    if (seconds === null) return;
    const deadline = Date.now() + seconds * 1000;
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left <= 0) {
        window.clearInterval(id);
        setPhaseIndex((index) => (index === phaseIndex ? index + 1 : index));
      }
    };
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [phaseIndex, running, done]);

  return { phase, phaseIndex, remaining: done ? 0 : remaining, done, running, advance, finish, start };
}

export function formatSeconds(total: number): string {
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
