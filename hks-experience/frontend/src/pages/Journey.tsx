import { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Step } from "../lib/api";
import { setLastStep } from "../lib/progress";
import { Sidebar } from "../components/Sidebar";
import { StepShell } from "../components/StepShell";
import { LoadingState, ErrorState } from "../components/EmptyState";
import { HpaVisual } from "../steps/HpaVisual";
import { BlueGreenVisual } from "../steps/BlueGreenVisual";
import { RollingUpdateVisual } from "../steps/RollingUpdateVisual";

export function Journey() {
  const { stepId } = useParams<{ stepId: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<Step[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Undefined while loading; false covers both hosted mode AND a
  // self-hosted portal with no kubeconfig mounted -- either way, every
  // step's automated Run/Verify is guaranteed to fail, so StepShell needs
  // to know this to lead with "run it yourself" instead of a doomed button.
  const [clusterConnected, setClusterConnected] = useState<boolean | undefined>(undefined);

  const reload = useCallback(() => {
    api.steps().then((d) => setSteps(d.steps)).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => { reload(); }, [reload]);
  useEffect(() => { api.info().then((i) => setClusterConnected(i.kubernetes.connected)).catch(() => setClusterConnected(false)); }, []);
  useEffect(() => { if (stepId) setLastStep(stepId); }, [stepId]);

  if (error) return <ErrorState message={error} />;
  if (!steps) return <LoadingState label="Loading your journey…" />;

  const current = steps.find((s) => s.id === stepId);
  if (!current) return <ErrorState message={`Unknown step '${stepId}'`} />;

  const idx = steps.findIndex((s) => s.id === stepId);
  const next = steps[idx + 1];
  const prev = steps[idx - 1];

  const goNext = () => {
    reload();
    if (next) navigate(`/journey/${next.id}`);
    else navigate("/summary");
  };
  const goBack = () => {
    if (prev) navigate(`/journey/${prev.id}`);
    else navigate("/");
  };

  return (
    <div className="flex">
      <Sidebar steps={steps} currentStepId={stepId} />
      <main className="min-w-0 flex-1 p-6 md:p-10">
        <p className="mb-6 text-xs font-label text-muted">Step {idx + 1} of {steps.length}</p>
        <StepShell
          step={current}
          onAdvance={goNext}
          onBack={goBack}
          clusterConnected={clusterConnected}
          extra={
            <>
              <HpaVisual stepId={current.id} />
              <BlueGreenVisual stepId={current.id} />
              <RollingUpdateVisual stepId={current.id} />
            </>
          }
        />
      </main>
    </div>
  );
}
