import { CheckCircle2, XCircle, MinusCircle, AlertTriangle, HelpCircle, CircleDashed } from "lucide-react";

const RESULT_META: Record<
  string,
  { label: string; icon: typeof CheckCircle2; className: string }
> = {
  PASS: { label: "PASS", icon: CheckCircle2, className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  FAIL: { label: "FAIL", icon: XCircle, className: "bg-red-50 text-red-700 border-red-200" },
  NOT_AVAILABLE: {
    label: "NOT AVAILABLE",
    icon: MinusCircle,
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  NOT_VALIDATED: {
    label: "NOT VALIDATED",
    icon: HelpCircle,
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  NOT_APPLICABLE: {
    label: "NOT APPLICABLE",
    icon: MinusCircle,
    className: "bg-slate-100 text-slate-600 border-slate-200",
  },
  BLOCKED: { label: "BLOCKED", icon: AlertTriangle, className: "bg-orange-50 text-orange-700 border-orange-200" },
  NOT_TESTED: { label: "NOT TESTED", icon: CircleDashed, className: "bg-slate-100 text-slate-600 border-slate-200" },
};

/** Never communicates status via color alone -- always paired with an icon
 * and explicit text label, per the product's accessibility requirements. */
export function StatusBadge({ result }: { result: string }) {
  const meta = RESULT_META[result] ?? RESULT_META.NOT_TESTED;
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-subheading ${meta.className}`}
    >
      <Icon size={14} aria-hidden="true" />
      {meta.label}
    </span>
  );
}
