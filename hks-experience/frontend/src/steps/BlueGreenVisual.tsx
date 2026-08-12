import { useState } from "react";
import { useLivePoll } from "../lib/livePoll";

interface BgLive {
  connected: boolean;
  active_track?: "blue" | "green" | string;
}

export function BlueGreenVisual({ stepId }: { stepId: string }) {
  const [watching, setWatching] = useState(false);
  const live = useLivePoll<BgLive>("/api/live/bluegreen", watching, 3000);
  if (stepId !== "blue-green") return null;

  const track = live?.connected ? live.active_track : undefined;

  return (
    <section className="card mb-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-subheading text-sm">Live traffic track</h2>
        <button onClick={() => setWatching((w) => !w)} className="btn-secondary !min-h-[32px] !py-1 text-xs">
          {watching ? "Stop watching" : "Watch live"}
        </button>
      </div>
      {!watching && <p className="text-sm text-muted">Click "Watch live" to poll the shared Service's real selector.</p>}
      {watching && (
        <div className="flex items-center justify-center gap-6 py-4">
          <div className={`rounded-card border-2 px-8 py-4 text-center transition-all ${track === "blue" ? "border-blue-500 bg-blue-50 shadow-card-hover" : "border-border opacity-50"}`}>
            <p className="font-heading text-lg text-blue-700">BLUE</p>
            <p className="text-xs text-muted">v1</p>
          </div>
          <div className="text-2xl text-muted">→</div>
          <div className={`rounded-card border-2 px-8 py-4 text-center transition-all ${track === "green" ? "border-emerald-500 bg-emerald-50 shadow-card-hover" : "border-border opacity-50"}`}>
            <p className="font-heading text-lg text-emerald-700">GREEN</p>
            <p className="text-xs text-muted">v2</p>
          </div>
        </div>
      )}
      {watching && live && !live.connected && <p className="text-center text-sm text-muted">Deploy blue/green first to see live traffic state.</p>}
    </section>
  );
}
