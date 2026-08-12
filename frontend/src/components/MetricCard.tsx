import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  icon: Icon,
  tone = "primary",
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  tone?: "primary" | "success" | "muted";
}) {
  const toneClass = {
    primary: "text-primary bg-indigo-50",
    success: "text-success bg-emerald-50",
    muted: "text-muted bg-slate-100",
  }[tone];

  return (
    <div className="card card-hover flex items-center gap-4">
      {Icon && (
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${toneClass}`}>
          <Icon size={22} aria-hidden="true" />
        </div>
      )}
      <div>
        <div className="text-2xl font-heading text-text">{value}</div>
        <div className="text-sm text-muted font-label">{label}</div>
      </div>
    </div>
  );
}
