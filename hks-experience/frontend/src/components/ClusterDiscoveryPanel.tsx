import { CheckCircle2, MinusCircle, HelpCircle } from "lucide-react";
import type { ClusterCapabilities } from "../lib/api";

const CAP_LABELS: Record<keyof ClusterCapabilities, string> = {
  cni: "CNI",
  storage: "Storage",
  prometheus: "Prometheus",
  ingress: "Ingress",
  gateway_api: "Gateway API",
  cluster_autoscaler: "Cluster Autoscaler",
};

function CapabilityRow({ label, value }: { label: string; value: string }) {
  const notDetected = value === "not_detected";
  const unknown = value === "unknown";
  const Icon = unknown ? HelpCircle : notDetected ? MinusCircle : CheckCircle2;
  const className = unknown ? "text-muted" : notDetected ? "text-muted" : "text-success";
  const display = value === "not_detected" ? "Not Detected" : value === "unknown" ? "Unknown" : value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
  return (
    <div className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className={`flex items-center gap-1.5 font-subheading ${className}`}>
        <Icon size={14} aria-hidden="true" />
        {display}
      </span>
    </div>
  );
}

/** The "beautiful discovery panel" for a successful Cluster Preparation --
 * optional capabilities are always shown as detected/not_detected/unknown,
 * never as a reason the overall step failed. */
export function ClusterDiscoveryPanel({
  cluster,
  capabilities,
}: {
  cluster: { context: string; version: string; nodes: number };
  capabilities: ClusterCapabilities;
}) {
  return (
    <div className="card mb-6">
      <div className="mb-3 flex items-center gap-2">
        <CheckCircle2 size={18} className="text-success" aria-hidden="true" />
        <h2 className="font-subheading">Cluster Preparation — Connected</h2>
      </div>
      <div className="mb-4 grid grid-cols-3 gap-4 text-sm">
        <div><p className="text-xs text-muted">Context</p><p className="font-subheading">{cluster.context}</p></div>
        <div><p className="text-xs text-muted">Kubernetes</p><p className="font-subheading">{cluster.version}</p></div>
        <div><p className="text-xs text-muted">Nodes</p><p className="font-subheading">{cluster.nodes}</p></div>
      </div>
      <p className="mb-1 text-xs font-label uppercase tracking-wide text-muted">Optional infrastructure</p>
      {(Object.keys(CAP_LABELS) as (keyof ClusterCapabilities)[]).map((key) => (
        <CapabilityRow key={key} label={CAP_LABELS[key]} value={capabilities[key]} />
      ))}
    </div>
  );
}
