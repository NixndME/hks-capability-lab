import { useState } from "react";
import { ChevronLeft, ChevronRight, SkipForward, PlayCircle, HelpCircle, CheckCircle2, Download, Package } from "lucide-react";
import type { RunResult, Step, StructuredError } from "../lib/api";
import { api } from "../lib/api";
import { CodeBlock } from "./CodeBlock";
import { CommandLine } from "./CommandLine";
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
  clusterConnected,
}: {
  step: Step;
  onAdvance: () => void;
  onBack: () => void;
  /** Optional rich visualization rendered above the generic action panel --
   * used by steps/*.tsx for the "aha moment" steps (HPA, blue/green, etc). */
  extra?: React.ReactNode;
  /** undefined while still loading; false covers hosted mode AND a
   * self-hosted portal with no kubeconfig mounted -- either way, an
   * automated Run/Verify is guaranteed to fail here, so it's shown as a
   * secondary, optional action instead of the primary CTA (see
   * ../pages/Journey.tsx, which fetches this once via api.info()). */
  clusterConnected?: boolean;
}) {
  const [mode, setMode] = useState<"yaml" | "helm">(step.deploy?.yaml ? "yaml" : "helm");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [confirmSkip, setConfirmSkip] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  const [downloadingChart, setDownloadingChart] = useState(false);

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
        remediation: ["Check that this portal's container is still running.", String(e)],
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

  const downloadChart = async () => {
    setDownloadingChart(true);
    setChartError(null);
    try {
      const res = await fetch(api.helmChartUrl, { credentials: "include" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const disposition = res.headers.get("content-disposition") ?? "";
      const filename = /filename=([^;]+)/.exec(disposition)?.[1]?.trim() ?? "hks-capability-lab.tgz";
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      // Never let a failed download silently save a broken/misnamed file --
      // fetch-and-check first, show a real message on failure instead.
      setChartError(String(e instanceof Error ? e.message : e));
    } finally {
      setDownloadingChart(false);
    }
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

          {mode === "yaml" && step.deploy?.yaml && (
            <div className="space-y-4">
              {!!step.deploy.yaml.resources?.length && (
                <div className="rounded-card border border-border bg-slate-50 p-3">
                  <p className="mb-2 font-subheading text-xs uppercase tracking-wide text-muted">What this YAML creates</p>
                  <ul className="space-y-1 text-sm">
                    {step.deploy.yaml.resources.map((r) => (
                      <li key={`${r.kind}/${r.name}`} className="flex items-baseline gap-2">
                        <span className="font-subheading text-text">{r.kind}</span>
                        <span className="text-muted">{r.name}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {step.deploy.yaml.content && (
                <div>
                  <p className="mb-1.5 font-subheading text-sm">YAML — {step.deploy.yaml.filename}</p>
                  <CodeBlock filename={step.deploy.yaml.filename ?? `${step.id}.yaml`} code={step.deploy.yaml.content} />
                </div>
              )}

              {step.deploy.yaml.apply_command ? (
                <CommandLine
                  label="Apply this YAML"
                  command={step.deploy.yaml.apply_command}
                  href={step.deploy.yaml.raw_url ?? undefined}
                  hrefLabel="Open Raw GitHub"
                />
              ) : (
                <p className="text-sm text-muted">
                  Couldn't determine this repository's public GitHub URL — download the YAML above and apply it directly:
                  <code className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs">kubectl apply -f {step.deploy.yaml.filename}</code>
                </p>
              )}

              {!!step.deploy.yaml.commands?.length && (
                <div>
                  <p className="mb-1.5 font-subheading text-sm text-muted">Additional commands for this step</p>
                  <CodeBlock filename={`${step.id}-extra.sh`} code={step.deploy.yaml.commands.join("\n")} />
                </div>
              )}
            </div>
          )}

          {mode === "helm" && step.deploy?.helm && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between rounded-card border border-border bg-slate-50 p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Package size={16} className="text-primary" aria-hidden="true" />
                    <span className="font-subheading">{step.deploy.helm.chart}</span>
                  </div>
                  <button onClick={downloadChart} disabled={downloadingChart} className="btn-secondary !min-h-[32px] !py-1 text-xs">
                    <Download size={14} aria-hidden="true" /> {downloadingChart ? "Downloading…" : "Download Chart"}
                  </button>
                </div>
                {chartError && (
                  <p className="mt-2 text-xs text-danger">
                    Couldn't download the chart: {chartError}. This is a portal deployment issue, not something wrong with your command below — the <code className="rounded bg-slate-100 px-1 py-0.5">helm install</code> command still works once you point it at your own copy of the chart.
                  </p>
                )}
              </div>
              <div>
                <p className="mb-1.5 font-subheading text-sm">Install</p>
                <CodeBlock filename={`${step.id}-helm.sh`} code={step.deploy.helm.commands.join("\n")} />
              </div>
            </div>
          )}
        </section>
      )}

      {!!step.manual_commands?.length && (
        <section className="mb-6">
          <h2 className="mb-2 font-subheading text-sm">Run this</h2>
          <div className="space-y-2">
            {step.manual_commands.map((cmd) => (
              <CommandLine key={cmd} command={cmd} />
            ))}
          </div>
        </section>
      )}

      <section className="mb-6 card">
        <h2 className="mb-1 font-subheading text-sm">Expected result</h2>
        <p className="mb-4 text-sm text-muted">{step.expected_result}</p>

        {canRun ? (
          clusterConnected === false ? (
            <div>
              <p className="mb-2 flex items-center gap-2 text-sm text-muted">
                <HelpCircle size={16} className="shrink-0" aria-hidden="true" />
                This portal isn't connected to a live cluster, so this automated check can't run here. Run the command(s) above yourself, then click Continue below.
              </p>
              <button onClick={run} disabled={running} className="btn-secondary">
                <PlayCircle size={16} aria-hidden="true" />
                {running ? "Checking…" : "Try Run / Verify anyway"}
              </button>
            </div>
          ) : (
            <button onClick={run} disabled={running} className="btn-primary">
              <PlayCircle size={16} aria-hidden="true" />
              {running ? "Checking…" : "Run / Verify"}
            </button>
          )
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted">
            <HelpCircle size={16} aria-hidden="true" />
            {activeDeploy || step.manual_commands?.length
              ? "No automated check for this step — run the command(s) above yourself, then continue."
              : "No automated check for this step — follow the instructions above, then continue."}
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
