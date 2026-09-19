import { useEffect, useRef, useState } from "react";

/**
 * Counts down to a deadline set by the server.
 *
 * The server decides every deadline, so the browser only displays it. The clock keeps the offset
 * between the server's time and this computer's clock, so a wrong local clock, a refresh or a new
 * tab can't buy extra time.
 */
export function useServerClock(deadline: string | null, serverTime: string | null): number | null {
  const offset = useRef(0);
  if (serverTime) {
    offset.current = new Date(serverTime).getTime() - Date.now();
  }
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!deadline) {
      setRemaining(null);
      return;
    }
    const left = () => Math.max(0, Math.round((new Date(deadline).getTime() - (Date.now() + offset.current)) / 1000));
    setRemaining(left());
    const id = window.setInterval(() => {
      const value = left();
      setRemaining(value);
      if (value <= 0) window.clearInterval(id);
    }, 250);
    return () => window.clearInterval(id);
  }, [deadline]);

  return remaining;
}
