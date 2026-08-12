import { CheckCircle2, Circle, XCircle, MinusCircle, Loader2, AlertTriangle } from "lucide-react";
import type { StepStatus } from "../lib/api";

const META: Record<StepStatus, { icon: typeof CheckCircle2; className: string; label: string }> = {
  COMPLETED: { icon: CheckCircle2, className: "text-success", label: "Completed" },
  SKIPPED: { icon: MinusCircle, className: "text-muted", label: "Skipped" },
  FAILED: { icon: XCircle, className: "text-danger", label: "Failed" },
  NOT_APPLICABLE: { icon: MinusCircle, className: "text-muted", label: "Not applicable" },
  IN_PROGRESS: { icon: Loader2, className: "text-primary animate-spin", label: "In progress" },
  AVAILABLE: { icon: Circle, className: "text-muted", label: "Available" },
  // BLOCKED is distinct from FAILED: a prerequisite (cluster connectivity,
  // RBAC) is missing -- the capability test itself never ran, so it's
  // never coded/colored as a failure.
  BLOCKED: { icon: AlertTriangle, className: "text-warning", label: "Blocked" },
};

export function StatusIcon({ status, size = 16 }: { status: StepStatus; size?: number }) {
  const meta = META[status] ?? META.AVAILABLE;
  const Icon = meta.icon;
  return <Icon size={size} className={meta.className} aria-hidden="true" />;
}

export function statusLabel(status: StepStatus): string {
  return (META[status] ?? META.AVAILABLE).label;
}

export function StepStatusBadge({ status }: { status: StepStatus }) {
  const meta = META[status] ?? META.AVAILABLE;
  const Icon = meta.icon;
  const bg: Record<StepStatus, string> = {
    COMPLETED: "bg-emerald-50 text-emerald-700 border-emerald-200",
    SKIPPED: "bg-slate-100 text-slate-600 border-slate-200",
    FAILED: "bg-red-50 text-red-700 border-red-200",
    NOT_APPLICABLE: "bg-slate-100 text-slate-600 border-slate-200",
    IN_PROGRESS: "bg-indigo-50 text-primary border-indigo-200",
    AVAILABLE: "bg-slate-50 text-muted border-border",
    BLOCKED: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-subheading ${bg[status]}`}>
      <Icon size={13} aria-hidden="true" className={status === "IN_PROGRESS" ? "animate-spin" : ""} />
      {meta.label}
    </span>
  );
}
