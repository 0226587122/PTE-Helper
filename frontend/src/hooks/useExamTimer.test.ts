import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { formatSeconds, useExamTimer, type TimerPhase } from "./useExamTimer";

const PHASES: TimerPhase[] = [
  { id: "leadin", label: "Audio starts in", seconds: 3 },
  { id: "audio", label: "Listening", seconds: null },
  { id: "prep", label: "Prepare", seconds: 10 },
  { id: "answer", label: "Recording", seconds: 40 },
];

describe("useExamTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts down a timed phase and moves on automatically", () => {
    const { result } = renderHook(() => useExamTimer(PHASES));
    expect(result.current.phase?.id).toBe("leadin");
    expect(result.current.remaining).toBe(3);

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.remaining).toBe(2);

    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(result.current.phase?.id).toBe("audio");
    expect(result.current.remaining).toBeNull();
  });

  it("waits on untimed phases until advance is called", () => {
    const { result } = renderHook(() => useExamTimer(PHASES));
    act(() => {
      vi.advanceTimersByTime(3500);
    });
    expect(result.current.phase?.id).toBe("audio");

    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(result.current.phase?.id).toBe("audio");

    act(() => result.current.advance());
    expect(result.current.phase?.id).toBe("prep");
    expect(result.current.remaining).toBe(10);
  });

  it("calls onPhaseStart for each phase and onComplete at the end", () => {
    const onPhaseStart = vi.fn();
    const onComplete = vi.fn();
    const phases: TimerPhase[] = [
      { id: "prep", label: "Prepare", seconds: 2 },
      { id: "answer", label: "Answer", seconds: 3 },
    ];
    const { result } = renderHook(() => useExamTimer(phases, { onPhaseStart, onComplete }));

    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(onPhaseStart).toHaveBeenCalledTimes(2);
    expect(onPhaseStart.mock.calls[1][0].id).toBe("answer");
    expect(onComplete).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(3100);
    });
    expect(result.current.done).toBe(true);
    expect(result.current.remaining).toBe(0);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("finish ends every phase at once", () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useExamTimer(PHASES, { onComplete }));
    act(() => result.current.finish());
    expect(result.current.done).toBe(true);
    expect(result.current.phase).toBeNull();
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("does nothing until started when autoStart is false", () => {
    const onPhaseStart = vi.fn();
    const { result } = renderHook(() => useExamTimer(PHASES, { autoStart: false, onPhaseStart }));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.phase?.id).toBe("leadin");
    expect(onPhaseStart).not.toHaveBeenCalled();

    act(() => result.current.start());
    expect(onPhaseStart).toHaveBeenCalledTimes(1);
  });

  it("formats seconds as minutes and seconds", () => {
    expect(formatSeconds(600)).toBe("10:00");
    expect(formatSeconds(65)).toBe("1:05");
    expect(formatSeconds(9)).toBe("0:09");
  });
});
