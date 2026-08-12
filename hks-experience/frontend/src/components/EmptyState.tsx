import type { LucideIcon } from "lucide-react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex min-h-[40vh] items-center justify-center gap-3 text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
      <span className="font-label text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="card border-red-200 bg-red-50 text-red-700">
      <p className="font-subheading text-sm">Something went wrong</p>
      <p className="mt-1 text-sm">{message}</p>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description }: { icon: LucideIcon; title: string; description?: string }) {
  return (
    <div className="card flex flex-col items-center gap-3 py-16 text-center">
      <Icon size={40} className="text-muted" aria-hidden="true" />
      <h3 className="font-heading text-lg">{title}</h3>
      {description && <p className="max-w-md text-sm text-muted">{description}</p>}
    </div>
  );
}
