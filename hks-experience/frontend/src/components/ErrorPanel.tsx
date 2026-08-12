import { useState } from "react";
import { AlertTriangle, Copy, Check, RotateCcw, ChevronDown } from "lucide-react";
import type { StructuredError } from "../lib/api";

const CODE_TITLES: Record<string, string> = {
  KUBECONFIG_NOT_FOUND: "Unable to connect to Kubernetes",
  KUBECONFIG_INVALID: "Kubernetes configuration is invalid",
  KUBERNETES_CONNECTION_FAILED: "Kubernetes API unreachable",
  KUBERNETES_AUTH_FAILED: "Kubernetes authentication failed",
  KUBERNETES_FORBIDDEN: "Kubernetes access denied",
  KUBERNETES_TIMEOUT: "Kubernetes API timed out",
  KUBERNETES_API_ERROR: "Kubernetes API error",
  INTERNAL_ERROR: "Something went wrong in this app",
  HOSTED_MODE_NOT_EXECUTED: "Not available in hosted mode",
};

/** Structured error/blocked display: title, what happened, remediation
 * (with a copyable command when one is present), collapsible technical
 * details, and a working Retry -- replaces the old "Actual result: ERROR"
 * dead end. */
export function ErrorPanel({ error, onRetry, retrying }: { error: StructuredError; onRetry: () => void; retrying: boolean }) {
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Kubernetes-journey remediations are always kubectl or plain prose --
  // never podman/docker (that only ever appears in README's Local
  // Installation section, not inside the guided journey itself).
  const commandLine = error.remediation.find((r) => r.trim().startsWith("kubectl"));
  const proseLines = error.remediation.filter((r) => r !== commandLine);

  const copyCommand = async () => {
    if (!commandLine) return;
    await navigator.clipboard.writeText(commandLine);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="rounded-card border border-amber-200 bg-amber-50 p-4" role="alert">
      <div className="mb-2 flex items-center gap-2">
        <AlertTriangle size={18} className="text-warning" aria-hidden="true" />
        <p className="font-subheading text-amber-900">✕ {CODE_TITLES[error.code] ?? error.message}</p>
      </div>

      {proseLines.length > 0 && (
        <div className="mb-3 space-y-1 text-sm text-amber-900">
          {proseLines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      )}

      {commandLine && (
        <div className="mb-3 flex items-center gap-2 rounded-lg bg-[#0F172A] px-3 py-2">
          <code className="flex-1 overflow-x-auto whitespace-pre text-xs text-slate-200">{commandLine}</code>
          <button onClick={copyCommand} className="flex shrink-0 items-center gap-1 text-xs text-slate-300 hover:text-white" aria-label="Copy command">
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      )}

      {error.details && (
        <div className="mb-3">
          <button onClick={() => setShowDetails((s) => !s)} className="flex items-center gap-1 text-xs font-subheading text-amber-800">
            <ChevronDown size={14} className={showDetails ? "rotate-180" : ""} aria-hidden="true" />
            Technical details
          </button>
          {showDetails && <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-white/60 p-2 text-xs text-amber-900">{error.details}</pre>}
        </div>
      )}

      <button onClick={onRetry} disabled={retrying} className="btn-secondary !min-h-[36px] !py-1.5 text-sm">
        <RotateCcw size={14} aria-hidden="true" />
        {retrying ? "Retrying…" : "Retry"}
      </button>
    </div>
  );
}
