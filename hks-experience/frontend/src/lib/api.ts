export type StepStatus =
  | "AVAILABLE" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED" | "FAILED" | "NOT_APPLICABLE" | "BLOCKED";

export interface ArtifactResource {
  kind: string;
  name: string;
}

export interface YamlDeployMode {
  /** Extra, kubectl-only follow-up commands (rollout status, discovery) --
   * never the apply command itself, which is always derived from raw_url. */
  commands: string[];
  /** public_artifacts id, e.g. "namespace" -- present once hydrated by the
   * backend's workflow.py against ../../../yaml/. */
  id?: string;
  filename?: string;
  name?: string;
  description?: string;
  resources?: ArtifactResource[];
  /** Full raw GitHub URL, or null if the repo origin couldn't be
   * determined (see backend/app/config.py's public_yaml_url). */
  raw_url?: string | null;
  /** `kubectl apply -f <raw_url>`, or null alongside raw_url. */
  apply_command?: string | null;
  /** The YAML file's exact text content, for View/Copy/Download without a
   * live GitHub round-trip. */
  content?: string | null;
}

export interface HelmDeployMode {
  chart?: string;
  commands: string[];
}

export interface Step {
  id: string;
  category: string;
  order: number;
  title: string;
  skippable: boolean;
  prerequisites: string[];
  test_ref: string[];
  what: string;
  why: string;
  what_you_will_do: string[];
  deploy: { yaml?: YamlDeployMode; helm?: HelmDeployMode } | null;
  /** Plain kubectl commands shown for steps with no deployable manifest at
   * all (port-forward, rollback, a blue/green traffic switch) -- see
   * workflows/README.md's schema note. */
  manual_commands?: string[];
  verify: { description: string; success_conditions: string[]; executor: string | null };
  expected_result: string;
  learn_more: string | null;
  status: StepStatus;
}

export interface StructuredError {
  code: string;
  message: string;
  remediation: string[];
  details?: string | null;
}

export interface AppInfo {
  application: string;
  display_name: string;
  version: string;
  mode: "hosted" | "local";
  execution_enabled: boolean;
  public_base_url: string;
  image_repository: string;
  timestamp: string;
  kubernetes: {
    connected: boolean;
    context: string | null;
    version: string | null;
    node_count: number | null;
    error: StructuredError | null;
  };
}

export interface ClusterCapabilities {
  cni: string;
  storage: string;
  prometheus: string;
  ingress: string;
  gateway_api: string;
  cluster_autoscaler: string;
}

export interface RunResult {
  step_id: string;
  executed: boolean;
  result: "PASS" | "FAIL" | "SKIP" | "BLOCKED" | "NOT_EXECUTED" | "ERROR";
  status: StepStatus;
  log: string[];
  error: StructuredError | null;
  cluster_status?: {
    status: "ready" | "blocked";
    cluster?: { context: string; version: string; nodes: number };
    capabilities?: ClusterCapabilities;
  };
}

export interface Summary {
  total: number;
  counts: Record<string, number>;
  categories: Record<string, { id: string; title: string; status: StepStatus }[]>;
  complete: boolean;
}

const opts: RequestInit = { credentials: "include" };

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(path, { ...opts, method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  info: () => get<AppInfo>("/api/info"),
  steps: () => get<{ steps: Step[]; categories: string[] }>("/api/steps"),
  step: (id: string) => get<Step>(`/api/steps/${id}`),
  run: (id: string) => post<RunResult>(`/api/steps/${id}/run`),
  skip: (id: string) => post<{ step_id: string; status: StepStatus }>(`/api/steps/${id}/skip`),
  summary: () => get<Summary>("/api/summary"),
  clusterStatus: () => get<Record<string, unknown>>("/api/cluster/status"),
  bundleUrl: "/api/artifacts/bundle.zip",
  helmChartUrl: "/api/public-yaml/helm-chart.tgz",
};
