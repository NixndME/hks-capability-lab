import { useState } from "react";
import { useLivePoll } from "../lib/livePoll";

interface DeployLive {
  connected: boolean;
  ready_replicas?: number;
  updated_replicas?: number;
  replicas?: number;
  version?: string;
}

export function RollingUpdateVisual({ stepId }: { stepId: string }) {
  const [watching, setWatching] = useState(false);
  const live = useLivePoll<DeployLive>("/api/live/deployment", watching, 2500);
  if (stepId !== "rolling-update" && stepId !== "rollback") return null;

  return (
    <section className="card mb-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-subheading text-sm">Live rollout state</h2>
        <button onClick={() => setWatching((w) => !w)} className="btn-secondary !min-h-[32px] !py-1 text-xs">
          {watching ? "Stop watching" : "Watch live"}
        </button>
      </div>
      {watching && live?.connected && (
        <div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${((live.updated_replicas ?? 0) / Math.max(live.replicas ?? 1, 1)) * 100}%` }}
            />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
            <div><p className="text-xs text-muted">Current version</p><p className="font-heading text-lg">{live.version}</p></div>
            <div><p className="text-xs text-muted">Ready</p><p className="font-heading text-lg">{live.ready_replicas}/{live.replicas}</p></div>
            <div><p className="text-xs text-muted">Updated</p><p className="font-heading text-lg">{live.updated_replicas}/{live.replicas}</p></div>
          </div>
        </div>
      )}
      {watching && live && !live.connected && <p className="text-sm text-muted">Deploy the application first.</p>}
    </section>
  );
}
