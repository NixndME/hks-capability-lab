import { NavLink } from "react-router-dom";
import type { Step } from "../lib/api";
import { StatusIcon } from "./StatusIcon";

export function Sidebar({ steps, currentStepId }: { steps: Step[]; currentStepId?: string }) {
  const categories: string[] = [];
  for (const s of steps) if (!categories.includes(s.category)) categories.push(s.category);

  const completed = steps.filter((s) => s.status === "COMPLETED" || s.status === "SKIPPED").length;

  return (
    <nav aria-label="Journey progress" className="sticky top-0 hidden h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-border bg-surface p-4 md:flex">
      <div className="mb-5 px-2">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white font-heading shadow-primary">H</div>
          <div className="font-heading text-sm leading-tight">HKS Capability Journey</div>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={steps.length}>
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${(completed / Math.max(steps.length, 1)) * 100}%` }} />
        </div>
        <p className="mt-1.5 text-xs text-muted">{completed} of {steps.length} steps done</p>
      </div>

      {categories.map((cat) => (
        <div key={cat} className="mb-4">
          <p className="mb-1 px-2 text-xs font-subheading uppercase tracking-wide text-muted">{cat}</p>
          <ul>
            {steps.filter((s) => s.category === cat).map((s) => (
              <li key={s.id}>
                <NavLink
                  to={s.status === "LOCKED" ? "#" : `/journey/${s.id}`}
                  aria-disabled={s.status === "LOCKED"}
                  onClick={(e) => { if (s.status === "LOCKED") e.preventDefault(); }}
                  className={({ isActive }) =>
                    `flex min-h-[40px] items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm ${
                      isActive || s.id === currentStepId ? "bg-indigo-50 text-primary font-subheading" : s.status === "LOCKED" ? "text-slate-300 cursor-not-allowed" : "text-text hover:bg-slate-50"
                    }`
                  }
                >
                  <StatusIcon status={s.status} />
                  <span className="truncate">{s.title}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
