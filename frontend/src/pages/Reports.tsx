import { FileJson, FileText, FileCode } from "lucide-react";

const FORMATS = [
  { href: "/api/reports/html", label: "HTML Report", icon: FileCode, desc: "Formatted report, open directly in a browser." },
  { href: "/api/reports/markdown", label: "Markdown Report", icon: FileText, desc: "Plain-text report for wikis, PRs, or docs." },
  { href: "/api/reports/json", label: "JSON Report", icon: FileJson, desc: "Machine-readable, for CI or further tooling." },
];

export function Reports() {
  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="font-heading text-2xl">Reports</h1>
        <p className="mt-1 text-sm text-muted">
          Generated from the recorded results in <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">tests/definitions/</code>,
          plus live (read-only) cluster connection status when available. Reports describe what was last validated and
          recorded — they do not re-run tests.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {FORMATS.map(({ href, label, icon: Icon, desc }) => (
          <a key={href} href={href} target="_blank" rel="noreferrer" className="card card-hover flex flex-col gap-2 hover:-translate-y-0.5">
            <Icon size={22} className="text-primary" aria-hidden="true" />
            <h2 className="font-subheading">{label}</h2>
            <p className="text-sm text-muted">{desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
