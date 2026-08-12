import { useState } from "react";
import { useLivePoll } from "../lib/livePoll";

interface HpaLive {
  connected: boolean;
  replicas?: number;
  min_replicas?: number;
  max_replicas?: number;
  target_cpu?: number;
  current_cpu?: number;
}

/** Real replica-count visualization for the HPA/CPU-load steps -- polls the
 * backend's read-only /api/live/hpa (which reads the actual HPA object),
 * never fabricates a number. */
export function HpaVisual({ stepId }: { stepId: string }) {
  const [watching, setWatching] = useState(false);
  const live = useLivePoll<HpaLive>("/api/live/hpa", watching, 4000);

  if (stepId !== "hpa" && stepId !== "cpu-load") return null;

  return (
    <section className="card mb-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-subheading text-sm">Live replica count</h2>
        <button onClick={() => setWatching((w) => !w)} className="btn-secondary !min-h-[32px] !py-1 text-xs">
          {watching ? "Stop watching" : "Watch live"}
        </button>
      </div>
      {!watching && <p className="text-sm text-muted">Click "Watch live" to poll the real HPA object every few seconds.</p>}
      {watching && !live && <p className="text-sm text-muted">Connecting…</p>}
      {watching && live && !live.connected && <p className="text-sm text-danger">Could not reach the cluster: {(live as { error?: string }).error}</p>}
      {watching && live?.connected && (
        <div>
          <div className="flex items-end gap-1" aria-label={`${live.replicas} replicas`}>
            {Array.from({ length: live.max_replicas ?? 6 }).map((_, i) => (
              <div
                key={i}
                className={`h-10 w-8 rounded-t-md transition-all duration-500 ${i < (live.replicas ?? 0) ? "bg-primary" : "bg-slate-100"}`}
                style={{ height: i < (live.replicas ?? 0) ? "40px" : "12px" }}
              />
            ))}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
            <div><p className="text-xs text-muted">Replicas</p><p className="font-heading text-lg">{live.replicas}</p></div>
            <div><p className="text-xs text-muted">Target CPU</p><p className="font-heading text-lg">{live.target_cpu}%</p></div>
            <div><p className="text-xs text-muted">Current CPU</p><p className="font-heading text-lg">{live.current_cpu ?? "—"}%</p></div>
          </div>
        </div>
      )}
    </section>
  );
}
