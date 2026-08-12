import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardCheck,
  Network,
  Gauge,
  Database,
  Activity,
  Rocket,
  Shield,
  HeartPulse,
  FileText,
  Server,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, type AppInfo } from "../lib/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/validation", label: "Validation", icon: ClipboardCheck },
  { to: "/category/Networking", label: "Networking", icon: Network },
  { to: "/category/Scaling", label: "Scaling", icon: Gauge },
  { to: "/category/Storage", label: "Storage", icon: Database },
  { to: "/category/Observability", label: "Observability", icon: Activity },
  { to: "/category/Deployments", label: "Deployments", icon: Rocket },
  { to: "/category/Security", label: "Security", icon: Shield },
  { to: "/category/Resiliency", label: "Resiliency", icon: HeartPulse },
  { to: "/reports", label: "Reports", icon: FileText },
];

export function Layout() {
  const [info, setInfo] = useState<AppInfo | null>(null);

  useEffect(() => {
    api.info().then(setInfo).catch(() => setInfo(null));
  }, []);

  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <div className="flex">
        <nav
          aria-label="Primary"
          className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-border bg-surface p-4 md:flex"
        >
          <div className="mb-6 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white font-heading shadow-primary">
              H
            </div>
            <div>
              <div className="font-heading text-sm leading-tight">HKS Capability Lab</div>
              <ModeChip info={info} />
            </div>
          </div>
          <ul className="flex flex-1 flex-col gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-label transition-colors ${
                      isActive ? "bg-indigo-50 text-primary" : "text-muted hover:bg-slate-50 hover:text-text"
                    }`
                  }
                >
                  <Icon size={18} aria-hidden="true" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
          <ClusterFooter info={info} />
        </nav>
        <main id="main-content" className="min-w-0 flex-1 p-6 md:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function ModeChip({ info }: { info: AppInfo | null }) {
  if (!info) return <div className="text-xs text-muted">Connecting…</div>;
  return (
    <div className="text-xs text-muted">
      {info.mode === "hosted" ? "HOSTED" : "LOCAL"} MODE
    </div>
  );
}

function ClusterFooter({ info }: { info: AppInfo | null }) {
  if (!info) return null;
  const k8s = info.kubernetes;
  return (
    <div className="mt-4 rounded-lg border border-border bg-slate-50 p-3 text-xs">
      <div className="flex items-center gap-2 font-subheading">
        <Server size={14} className={k8s.connected ? "text-success" : "text-muted"} aria-hidden="true" />
        Cluster Connection
      </div>
      {k8s.connected ? (
        <ul className="mt-1.5 space-y-0.5 text-muted">
          <li>✓ Connected — {k8s.context}</li>
          <li>Kubernetes {k8s.version}</li>
          <li>{k8s.node_count} nodes</li>
        </ul>
      ) : (
        <p className="mt-1.5 text-muted">
          {info.mode === "hosted"
            ? "— Not applicable in hosted mode"
            : "Not connected. Mount kubeconfig to enable automatic validation."}
        </p>
      )}
    </div>
  );
}
