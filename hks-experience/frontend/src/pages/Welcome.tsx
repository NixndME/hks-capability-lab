import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ListChecks } from "lucide-react";
import { api, type AppInfo, type Step } from "../lib/api";
import { getLastStep } from "../lib/progress";
import { LoadingState } from "../components/EmptyState";

export function Welcome() {
  const navigate = useNavigate();
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [steps, setSteps] = useState<Step[] | null>(null);
  const lastStep = getLastStep();

  useEffect(() => {
    Promise.all([api.info(), api.steps()]).then(([i, s]) => {
      setInfo(i);
      setSteps(s.steps);
    });
  }, []);

  if (!info || !steps) return <LoadingState />;

  const lastStepDef = lastStep ? steps.find((s) => s.id === lastStep) : null;
  const firstAvailable = steps.find((s) => s.status !== "COMPLETED") ?? steps[0];

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="relative w-full max-w-xl overflow-hidden rounded-card border border-border bg-surface p-10 shadow-card text-center">
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div aria-hidden="true" className="pointer-events-none absolute -left-20 bottom-0 h-56 w-56 rounded-full bg-violet-200/30 blur-3xl" />

        <div className="relative">
          <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white font-display text-2xl shadow-primary">H</div>
          <h1 className="font-display text-3xl">Welcome to HKS Capability Lab</h1>
          <p className="mx-auto mt-4 max-w-md text-muted">
            Let's validate your Kubernetes platform step by step. You can
            complete the full journey, or skip any step and come back later.
          </p>

          {info.mode === "local" && (
            <p className="mt-4 text-xs text-muted">
              {info.kubernetes.connected
                ? `Connected to ${info.kubernetes.context} · Kubernetes ${info.kubernetes.version} · ${info.kubernetes.node_count} nodes`
                : "No cluster connected yet — you can still browse the journey and every command."}
            </p>
          )}

          <div className="mt-8 flex flex-col items-center gap-3">
            {lastStepDef && (
              <button onClick={() => navigate(`/journey/${lastStepDef.id}`)} className="btn-secondary w-full max-w-xs">
                Continue where you left off — {lastStepDef.title}
              </button>
            )}
            <button onClick={() => navigate(`/journey/${firstAvailable.id}`)} className="btn-primary w-full max-w-xs">
              Start Validation <ArrowRight size={16} aria-hidden="true" />
            </button>
            <button onClick={() => navigate("/summary")} className="btn-ghost w-full max-w-xs">
              <ListChecks size={16} aria-hidden="true" /> View journey overview
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
