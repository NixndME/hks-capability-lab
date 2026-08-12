export type StepStatus =
  | "LOCKED" | "AVAILABLE" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED" | "FAILED" | "NOT_APPLICABLE" | "BLOCKED";

export interface DeployMode {
  artifact?: string;
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
  deploy: { yaml?: DeployMode; helm?: DeployMode } | null;
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
};
