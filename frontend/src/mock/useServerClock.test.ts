import { renderHook } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerClock } from "./useServerClock";

describe("useServerClock", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-18T10:00:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts down to the deadline the server gave", () => {
    const { result } = renderHook(() =>
      useServerClock("2026-09-18T10:01:00Z", "2026-09-18T10:00:00Z"),
    );
    expect(result.current).toBe(60);

    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(result.current).toBe(50);
  });

  it("uses the server's clock, not this computer's", () => {
    // This computer is 5 minutes fast, so a naive countdown would show 55 seconds.
    const { result } = renderHook(() =>
      useServerClock("2026-09-18T10:06:00Z", "2026-09-18T10:05:00Z"),
    );
    expect(result.current).toBe(60);
  });

  it("stops at zero and never goes negative", () => {
    const { result } = renderHook(() => useServerClock("2026-09-18T10:00:05Z", "2026-09-18T10:00:00Z"));
    act(() => {
      vi.advanceTimersByTime(20_000);
    });
    expect(result.current).toBe(0);
  });

  it("has no clock when there is no deadline", () => {
    const { result } = renderHook(() => useServerClock(null, "2026-09-18T10:00:00Z"));
    expect(result.current).toBeNull();
  });
});
