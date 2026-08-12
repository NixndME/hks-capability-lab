import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type MatrixRow } from "../lib/api";
import { LoadingState, ErrorState, EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { SearchX } from "lucide-react";

export function Validation() {
  const [rows, setRows] = useState<MatrixRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api
      .matrix()
      .then((m) => setRows(m.rows))
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) => r.id.toLowerCase().includes(q) || r.name.toLowerCase().includes(q) || r.category.toLowerCase().includes(q)
    );
  }, [rows, filter]);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <LoadingState label="Loading capability matrix…" />;

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="font-heading text-2xl">Capability Matrix</h1>
        <p className="mt-1 text-sm text-muted">
          Driven by <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">tests/definitions/*.yaml</code> — the
          same source of truth used by the CLI and generated reports.
        </p>
      </header>

      <label htmlFor="matrix-filter" className="sr-only">
        Filter capabilities
      </label>
      <input
        id="matrix-filter"
        type="text"
        placeholder="Filter by ID, name, or category…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-4 w-full max-w-sm rounded-lg border border-border px-3 py-2.5 text-sm focus:border-primary focus:outline-none"
      />

      {filtered.length === 0 ? (
        <EmptyState icon={SearchX} title="No matching capabilities" description="Try a different search term." />
      ) : (
        <div className="overflow-x-auto rounded-card border border-border bg-surface shadow-card">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left font-subheading">
              <tr>
                <th scope="col" className="px-4 py-3">ID</th>
                <th scope="col" className="px-4 py-3">Capability</th>
                <th scope="col" className="px-4 py-3">Category</th>
                <th scope="col" className="px-4 py-3">YAML</th>
                <th scope="col" className="px-4 py-3">Helm</th>
                <th scope="col" className="px-4 py-3">Result</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id} className="border-t border-border hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-muted">{row.id}</td>
                  <td className="px-4 py-3">
                    <Link to={`/test/${row.id}`} className="font-subheading text-text hover:text-primary">
                      {row.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted">{row.category}</td>
                  <td className="px-4 py-3">{row.yaml ? "✓ YAML" : "—"}</td>
                  <td className="px-4 py-3">{row.helm ? "✓ Helm" : "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge result={row.result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
