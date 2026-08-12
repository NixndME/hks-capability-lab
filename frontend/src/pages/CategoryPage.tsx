import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, type TestDefinition } from "../lib/api";
import { LoadingState, ErrorState, EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { FolderOpen } from "lucide-react";

export function CategoryPage() {
  const { category } = useParams<{ category: string }>();
  const [items, setItems] = useState<TestDefinition[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setItems(null);
    api
      .tests()
      .then((d) => setItems(d.categories[category ?? ""] ?? []))
      .catch((e) => setError(String(e)));
  }, [category]);

  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label={`Loading ${category}…`} />;

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="font-heading text-2xl">{category}</h1>
        <p className="mt-1 text-sm text-muted">{items.length} capability definitions in this category.</p>
      </header>

      {items.length === 0 ? (
        <EmptyState icon={FolderOpen} title="No definitions yet" description="This category has no test definitions." />
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={item.id}>
              <Link to={`/test/${item.id}`} className="card card-hover flex items-start justify-between gap-4 hover:-translate-y-0.5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted">{item.id}</span>
                    <h2 className="font-subheading">{item.name}</h2>
                  </div>
                  <p className="mt-1 text-sm text-muted">{item.description}</p>
                </div>
                <StatusBadge result={item.result} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
