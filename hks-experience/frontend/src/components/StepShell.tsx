import { useState } from "react";
import { ChevronLeft, ChevronRight, SkipForward, PlayCircle, HelpCircle, CheckCircle2 } from "lucide-react";
import type { RunResult, Step, StructuredError } from "../lib/api";
import { api } from "../lib/api";
import { CodeBlock } from "./CodeBlock";
import { StepStatusBadge } from "./StatusIcon";
import { ErrorPanel } from "./ErrorPanel";
import { ClusterDiscoveryPanel } from "./ClusterDiscoveryPanel";

// cluster-prep is the one step whose "Run / Verify" isn't driven by
// step.verify.executor (it's handled by a dedicated backend code path --
// see backend/app/routers/steps.py's _run_cluster_prep) so it needs to
// show the action button even though executor is null for this step.
const ALWAYS_RUNNABLE = new Set(["cluster-prep"]);

export function StepShell({
  step,
  onAdvance,
  onBack,
  extra,
}: {
  step: Step;
  onAdvance: () => void;
  onBack: () => void;
  /** Optional rich visualization rendered above the generic action panel --
   * used by steps/*.tsx for the "aha moment" steps (HPA, blue/green, etc). */
  extra?: React.ReactNode;
}) {
  const [mode, setMode] = useState<"yaml" | "helm">(step.deploy?.yaml ? "yaml" : "helm");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [confirmSkip, setConfirmSkip] = useState(false);

  const activeDeploy = step.deploy?.[mode];
  const hasBothModes = !!(step.deploy?.yaml && step.deploy?.helm);
  const canRun = !!step.verify.executor || ALWAYS_RUNNABLE.has(step.id);

  const run = async () => {
    setRunning(true);
    try {
      const r = await api.run(step.id);
      setResult(r);
    } catch (e) {
      // A network/API-level failure talking to OUR OWN backend -- still
      // never a bare "ERROR", always a structured, actionable message.
      const fallback: StructuredError = {
        code: "INTERNAL_ERROR",
        message: "Could not reach the portal backend.",
        remediation: ["Check the container is still running (podman ps).", String(e)],
      };
      setResult({ step_id: step.id, executed: false, result: "ERROR", status: "BLOCKED", log: [], error: fallback });
    } finally {
      setRunning(false);
    }
  };

  const skip = async () => {
    await api.skip(step.id);
    onAdvance();
  };

  const showsBlockedPanel = result?.error && (result.result === "BLOCKED" || result.result === "ERROR");
  const showsClusterPanel = step.id === "cluster-prep" && result?.cluster_status?.status === "ready" && result.cluster_status.cluster && result.cluster_status.capabilities;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-label text-xs uppercase tracking-wide text-primary">{step.category}</p>
        <StepStatusBadge status={step.status} />
      </div>
      <h1 className="mb-6 font-heading text-2xl">{step.title}</h1>

      <section className="mb-5">
        <h2 className="mb-1.5 font-subheading text-sm text-muted">What are we testing?</h2>
        <p className="text-text">{step.what}</p>
      </section>

      <section className="mb-5">
        <h2 className="mb-1.5 font-subheading text-sm text-muted">Why does this matter?</h2>
        <p className="text-text">{step.why}</p>
      </section>

      {step.what_you_will_do?.length > 0 && (
        <section className="card mb-6">
          <h2 className="mb-2 font-subheading text-sm">What you'll do</h2>
          <ol className="list-inside list-decimal space-y-1 text-sm text-muted">
            {step.what_you_will_do.map((line) => <li key={line}>{line}</li>)}
          </ol>
        </section>
      )}

      {extra}

      {showsClusterPanel && (
        <ClusterDiscoveryPanel cluster={result!.cluster_status!.cluster!} capabilities={result!.cluster_status!.capabilities!} />
      )}

      {activeDeploy && (
        <section className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-subheading text-sm">Deploy using</h2>
            {hasBothModes && (
              <div className="flex rounded-lg border border-border p-0.5">
                <button onClick={() => setMode("yaml")} className={`rounded-md px-3 py-1 text-xs font-subheading ${mode === "yaml" ? "bg-primary text-white" : "text-muted"}`}>
                  Kubernetes YAML
                </button>
                <button onClick={() => setMode("helm")} className={`rounded-md px-3 py-1 text-xs font-subheading ${mode === "helm" ? "bg-primary text-white" : "text-muted"}`}>
                  Helm
                </button>
              </div>
            )}
          </div>
          <CodeBlock filename={`${step.id}.sh`} code={activeDeploy.commands.join("\n")} />
        </section>
      )}

      <section className="mb-6 card">
        <h2 className="mb-1 font-subheading text-sm">Expected result</h2>
        <p className="mb-4 text-sm text-muted">{step.expected_result}</p>

        {canRun ? (
          <button onClick={run} disabled={running || step.status === "LOCKED"} className="btn-primary">
            <PlayCircle size={16} aria-hidden="true" />
            {running ? "Checking…" : "Run / Verify"}
          </button>
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted">
            <HelpCircle size={16} aria-hidden="true" />
            No automated check for this step — run the command above yourself, then continue.
          </p>
        )}

        {showsBlockedPanel && (
          <div className="mt-4">
            <ErrorPanel error={result!.error!} onRetry={run} retrying={running} />
          </div>
        )}

        {result && !showsBlockedPanel && !showsClusterPanel && (
          <div className="mt-4 rounded-lg border border-border bg-slate-50 p-3" role="status">
            <p className="mb-1 flex items-center gap-1.5 font-subheading text-sm">
              {result.result === "PASS" ? <CheckCircle2 size={15} className="text-success" aria-hidden="true" /> : null}
              Actual result: <span className={result.result === "PASS" ? "text-success" : result.result === "SKIP" ? "text-muted" : "text-danger"}>{result.result}</span>
            </p>
            <pre className="whitespace-pre-wrap font-mono text-xs text-muted">{result.log.join("\n")}</pre>
          </div>
        )}

        {result && showsClusterPanel && (
          <p className="mt-3 text-xs text-muted">See the panel above for full discovery details.</p>
        )}

        {step.learn_more && result?.result === "PASS" && (
          <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/60 p-3">
            <p className="font-subheading text-sm text-primary">Why did that happen?</p>
            <p className="mt-1 text-sm text-text">{step.learn_more}</p>
          </div>
        )}
      </section>

      <div className="flex items-center justify-between">
        <button onClick={onBack} className="btn-ghost"><ChevronLeft size={16} /> Back</button>
        <div className="flex gap-2">
          {step.skippable && step.status !== "COMPLETED" && (
            confirmSkip ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted">You can return later from the sidebar.</span>
                <button onClick={skip} className="btn-secondary">Confirm Skip</button>
                <button onClick={() => setConfirmSkip(false)} className="btn-ghost">Cancel</button>
              </div>
            ) : (
              <button onClick={() => setConfirmSkip(true)} className="btn-secondary"><SkipForward size={16} /> Skip this step</button>
            )
          )}
          <button onClick={onAdvance} className="btn-primary">Continue <ChevronRight size={16} /></button>
        </div>
      </div>
    </div>
  );
}
