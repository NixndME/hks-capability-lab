import { useEffect, useRef, useState } from "react";

/** Polls a JSON endpoint every `intervalMs` while `active` is true. Used by
 * the flagship steps for real (not fabricated) live visualizations. */
export function useLivePoll<T>(url: string, active: boolean, intervalMs = 3000) {
  const [data, setData] = useState<T | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch(url, { credentials: "include" });
        if (res.ok && !cancelled) setData(await res.json());
      } catch {
        // transient network error -- keep last known value, try again next tick
      }
    };
    if (active) {
      tick();
      timer.current = window.setInterval(tick, intervalMs);
    }
    return () => {
      cancelled = true;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [url, active, intervalMs]);

  return data;
}
