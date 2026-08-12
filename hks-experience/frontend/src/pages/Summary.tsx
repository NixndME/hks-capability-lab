import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, FileJson, Package } from "lucide-react";
import { api, type Summary as SummaryT } from "../lib/api";
import { LoadingState, ErrorState } from "../components/EmptyState";
import { StepStatusBadge } from "../components/StatusIcon";

export function Summary() {
  const [summary, setSummary] = useState<SummaryT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.summary().then(setSummary).catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!summary) return <LoadingState label="Building your summary…" />;

  const { counts, categories } = summary;

  return (
    <div className="mx-auto max-w-3xl p-6 md:p-10">
      <header className="mb-8 text-center">
        <h1 className="font-display text-3xl">HKS Validation {summary.complete ? "Complete" : "In Progress"}</h1>
        <p className="mt-3 text-muted">
          {counts.COMPLETED} completed · {counts.SKIPPED} skipped · {counts.NOT_APPLICABLE} not applicable · {counts.FAILED} failed
        </p>
      </header>

      <div className="mb-8 space-y-6">
        {Object.entries(categories).map(([cat, items]) => (
          <div key={cat} className="card">
            <h2 className="mb-3 font-subheading">{cat}</h2>
            <ul className="space-y-2">
              {items.map((item) => (
                <li key={item.id} className="flex items-center justify-between text-sm">
                  <Link to={`/journey/${item.id}`} className="hover:text-primary">{item.title}</Link>
                  <StepStatusBadge status={item.status} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <a href={api.bundleUrl} className="card flex flex-col items-center gap-2 py-6 text-center hover:-translate-y-0.5 hover:shadow-card-hover">
          <Package size={22} className="text-primary" />
          <span className="text-sm font-subheading">YAML + Helm Bundle</span>
        </a>
        <a href="/api/summary" className="card flex flex-col items-center gap-2 py-6 text-center hover:-translate-y-0.5 hover:shadow-card-hover">
          <FileJson size={22} className="text-primary" />
          <span className="text-sm font-subheading">JSON Summary</span>
        </a>
        <Link to="/" className="card flex flex-col items-center gap-2 py-6 text-center hover:-translate-y-0.5 hover:shadow-card-hover">
          <FileText size={22} className="text-primary" />
          <span className="text-sm font-subheading">Back to Welcome</span>
        </Link>
      </div>
    </div>
  );
}
