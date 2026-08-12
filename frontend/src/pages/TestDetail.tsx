import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { api, type TestDefinition } from "../lib/api";
import { LoadingState, ErrorState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { CodeBlock } from "../components/CodeBlock";

export function TestDetail() {
  const { id } = useParams<{ id: string }>();
  const [test, setTest] = useState<TestDefinition | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setTest(null);
    api.test(id).then(setTest).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!test) return <LoadingState label={`Loading ${id}…`} />;

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={`/category/${test.category}`} className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-primary">
        <ChevronLeft size={16} aria-hidden="true" /> Back to {test.category}
      </Link>

      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-muted">{test.id}</p>
          <h1 className="font-heading text-2xl">{test.name}</h1>
        </div>
        <StatusBadge result={test.result} />
      </header>

      <p className="mb-6 text-muted">{test.description}</p>
      {test.purpose && (
        <div className="card mb-6 border-indigo-100 bg-indigo-50/50">
          <p className="font-subheading text-sm text-primary">Why this matters</p>
          <p className="mt-1 text-sm text-text">{test.purpose}</p>
        </div>
      )}

      {test.result_notes && (
        <div className="card mb-6">
          <p className="font-subheading text-sm">Result notes</p>
          <p className="mt-1 text-sm text-muted">{test.result_notes}</p>
        </div>
      )}

      {test.commands?.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 font-subheading text-sm">Commands</h2>
          <CodeBlock filename={`${test.id}.sh`} code={test.commands.join("\n")} language="bash" />
        </section>
      )}

      {test.success_conditions?.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 font-subheading text-sm">Success conditions</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted">
            {test.success_conditions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {test.artifacts?.length > 0 && (
          <section>
            <h2 className="mb-2 font-subheading text-sm">Artifacts</h2>
            <ul className="space-y-1 text-sm text-muted">
              {test.artifacts.map((a) => (
                <li key={a} className="font-mono text-xs">{a}</li>
              ))}
            </ul>
          </section>
        )}
        {test.docs?.length > 0 && (
          <section>
            <h2 className="mb-2 font-subheading text-sm">Related docs</h2>
            <ul className="space-y-1 text-sm text-muted">
              {test.docs.map((d) => (
                <li key={d} className="font-mono text-xs">{d}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
