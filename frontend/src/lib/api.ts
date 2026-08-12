// Thin fetch wrapper around the portal backend's REST API. The browser only
// ever talks to this backend, never to Kubernetes directly (see
// backend/app/k8s.py) -- see the product's security rules.
export interface KubernetesInfo {
  connected: boolean;
  context: string | null;
  version: string | null;
  node_count: number | null;
  error: string | null;
}

export interface AppInfo {
  application: string;
  display_name: string;
  version: string;
  mode: "hosted" | "local";
  public_base_url: string;
  portal_domain: string;
  image_repository: string;
  timestamp: string;
  kubernetes: KubernetesInfo;
}

export interface MatrixRow {
  id: string;
  name: string;
  category: string;
  yaml: boolean;
  helm: boolean;
  result: string;
  result_notes: string | null;
  prerequisites: string[];
  last_validated: string | null;
}

export interface TestDefinition extends MatrixRow {
  description: string;
  purpose?: string;
  deployment_modes: string[];
  artifacts: string[];
  commands: string[];
  success_conditions: string[];
  evidence: string[];
  docs: string[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  info: () => get<AppInfo>("/api/info"),
  matrix: () => get<{ rows: MatrixRow[] }>("/api/matrix"),
  tests: () =>
    get<{ count: number; summary: Record<string, number>; categories: Record<string, TestDefinition[]> }>(
      "/api/tests"
    ),
  test: (id: string) => get<TestDefinition>(`/api/tests/${id}`),
  reportJson: () => get<Record<string, unknown>>("/api/reports/json"),
};
