import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ListChecks, AlertTriangle, HelpCircle, ArrowRight, BookOpen } from "lucide-react";
import { api, type AppInfo, type MatrixRow } from "../lib/api";
import { MetricCard } from "../components/MetricCard";
import { LoadingState, ErrorState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";

const CAPABILITY_GROUPS = ["Networking", "Storage", "Scaling", "Observability", "Deployments", "Security", "Resiliency"];

export function Dashboard() {
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [rows, setRows] = useState<MatrixRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.info(), api.matrix()])
      .then(([i, m]) => {
        setInfo(i);
        setRows(m.rows);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!rows || !info) return <LoadingState label="Loading dashboard…" />;

  const pass = rows.filter((r) => r.result === "PASS").length;
  const gaps = rows.filter((r) => r.result === "NOT_AVAILABLE" || r.result === "NOT_VALIDATED").length;
  const fail = rows.filter((r) => r.result === "FAIL").length;

  return (
    <div className="mx-auto max-w-6xl">
      <section className="relative mb-10 overflow-hidden rounded-card border border-border bg-gradient-to-br from-indigo-50 via-white to-violet-50 p-10">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl"
        />
        <p className="mb-2 font-label text-sm uppercase tracking-wide text-primary">
          {info.mode === "hosted" ? "Hosted" : "Local"} Mode
        </p>
        <h1 className="max-w-2xl font-display text-4xl leading-tight text-text">
          HKS Kubernetes Capability Validation
        </h1>
        <p className="mt-4 max-w-xl text-muted">
          Validate your HKS Kubernetes platform across networking, storage, scaling, observability,
          deployment lifecycle, security, and resiliency — with real evidence, not assumptions.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/validation" className="btn-primary">
            Start Validation <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <Link to="/validation" className="btn-secondary">
            <BookOpen size={16} aria-hidden="true" /> Explore Test Suite
          </Link>
        </div>
      </section>

      <section className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Summary metrics">
        <MetricCard label="Capabilities Tracked" value={rows.length} icon={ListChecks} tone="primary" />
        <MetricCard label="Passing" value={pass} icon={ShieldCheck} tone="success" />
        <MetricCard label="Infra / Scope Gaps" value={gaps} icon={HelpCircle} tone="muted" />
        <MetricCard label="Failing" value={fail} icon={AlertTriangle} tone={fail > 0 ? "primary" : "muted"} />
      </section>

      <section aria-label="Capability categories">
        <h2 className="mb-4 font-heading text-lg">Browse by category</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITY_GROUPS.map((cat) => {
            const catRows = rows.filter((r) => r.category === cat);
            const catPass = catRows.filter((r) => r.result === "PASS").length;
            return (
              <Link
                key={cat}
                to={`/category/${cat}`}
                className="card card-hover flex flex-col gap-2 hover:-translate-y-0.5"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-subheading">{cat}</h3>
                  <StatusBadge result={catPass === catRows.length && catRows.length > 0 ? "PASS" : "NOT_TESTED"} />
                </div>
                <p className="text-sm text-muted">
                  {catPass} / {catRows.length} passing
                </p>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
