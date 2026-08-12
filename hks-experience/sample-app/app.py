#!/usr/bin/env python3
"""
HKS Demo Workload -- the sample application driven by the guided
hks-experience journey (separate from ../../sample-app/app.py, which the
existing validator drives). Single-file, Python-stdlib-only, no image
build or private registry required -- same architectural discipline as the
existing sample app, new branding/UI, own design.

All figures shown are real: request counts, latencies, and resource usage
come from actual measurements (resource.getrusage, real request timing) --
this app never reports a cluster-wide replica count or traffic split,
because a single pod process cannot honestly know that; the portal
(which does have cluster API access) is responsible for anything that
requires seeing across pods.
"""
import json
import os
import resource
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

APP_NAME = "HKS Demo Workload"
APP_VERSION = os.environ.get("APP_VERSION", "v1")
COLOR = os.environ.get("APP_COLOR", "blue")
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())
NODE_NAME = os.environ.get("NODE_NAME", "unknown")
NAMESPACE = os.environ.get("POD_NAMESPACE", "unknown")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "app")
PORT = int(os.environ.get("APP_PORT", "8080"))
START_TIME = time.time()

STATE_LOCK = threading.Lock()
STATE = {
    "request_count": 0,
    "active_cpu_jobs": 0,
    "active_memory_jobs": 0,
    "readiness_fail_until": 0.0,
    "liveness_fail_until": 0.0,
    "recent_requests": [],  # list of (timestamp, method, path, status, duration_ms)
}
_MEMORY_BALLAST: list[bytearray] = []  # holds allocated memory during a memory-load job


def record_request(method, path, status, duration):
    with STATE_LOCK:
        STATE["request_count"] += 1
        STATE["recent_requests"].append(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
            }
        )
        STATE["recent_requests"] = STATE["recent_requests"][-25:]


def real_resource_usage():
    """Genuine OS-reported figures -- not synthetic. ru_utime/ru_stime are
    actual CPU seconds consumed by this process; ru_maxrss is real peak
    resident memory (KB on Linux)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "cpu_user_seconds": round(usage.ru_utime, 3),
        "cpu_system_seconds": round(usage.ru_stime, 3),
        "max_rss_kb": usage.ru_maxrss,
    }


def cpu_burn_worker(target_pct, stop_at):
    target_pct = max(0, min(100, target_pct))
    slice_s = 0.05
    busy = slice_s * (target_pct / 100.0)
    idle = slice_s - busy
    while time.time() < stop_at:
        t0 = time.time()
        while time.time() - t0 < busy:
            _ = sum(i * i for i in range(2000))
        if idle > 0:
            time.sleep(idle)


def start_cpu_load(cpu_pct, duration_s, concurrency):
    stop_at = time.time() + duration_s
    with STATE_LOCK:
        STATE["active_cpu_jobs"] += concurrency

    def run_and_decrement():
        cpu_burn_worker(cpu_pct, stop_at)
        with STATE_LOCK:
            STATE["active_cpu_jobs"] -= 1

    for _ in range(concurrency):
        threading.Thread(target=run_and_decrement, daemon=True).start()


def start_memory_load(mb, duration_s):
    """Bounded, safe: allocates real memory (visible in real_resource_usage's
    max_rss_kb) for duration_s, then releases it. Hard-capped to prevent
    accidental exhaustion."""
    mb = max(1, min(mb, 512))
    duration_s = max(1, min(duration_s, 300))
    with STATE_LOCK:
        STATE["active_memory_jobs"] += 1

    def run():
        block = bytearray(mb * 1024 * 1024)
        for i in range(0, len(block), 4096):  # touch every page so it's really resident
            block[i] = 1
        _MEMORY_BALLAST.append(block)
        time.sleep(duration_s)
        try:
            _MEMORY_BALLAST.remove(block)
        except ValueError:
            pass
        with STATE_LOCK:
            STATE["active_memory_jobs"] -= 1

    threading.Thread(target=run, daemon=True).start()


TRACK_COLORS = {"blue": "#4F46E5", "green": "#10B981", "canary": "#D97706"}


def render_index():
    accent = TRACK_COLORS.get(COLOR, "#4F46E5")
    uptime = round(time.time() - START_TIME, 1)
    return f"""<!doctype html>
<html lang="en"><head><title>{APP_NAME}</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
 :root {{ --bg:#F8FAFC; --surface:#FFFFFF; --primary:{accent}; --text:#0F172A; --muted:#64748B; --success:#10B981; --border:#E2E8F0; }}
 * {{ box-sizing:border-box; }}
 body {{ font-family:'Plus Jakarta Sans',-apple-system,'Segoe UI',Roboto,sans-serif; margin:0; background:var(--bg); color:var(--text); }}
 header {{ background:var(--surface); border-bottom:1px solid var(--border); padding:16px 32px; display:flex; align-items:center; justify-content:space-between; }}
 .brand {{ display:flex; align-items:center; gap:10px; font-weight:800; font-size:18px; }}
 .brand .mark {{ width:32px; height:32px; border-radius:8px; background:var(--primary); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; box-shadow:0 8px 24px rgba(79,70,229,.25); }}
 .track {{ padding:4px 12px; border-radius:999px; background:{accent}1a; color:{accent}; font-weight:600; font-size:12px; }}
 .wrap {{ padding:32px; max-width:1000px; margin:0 auto; }}
 .tabs {{ display:flex; gap:4px; margin-bottom:20px; border-bottom:1px solid var(--border); }}
 .tab {{ padding:10px 16px; font-weight:600; font-size:14px; color:var(--muted); cursor:pointer; border-bottom:2px solid transparent; min-height:44px; }}
 .tab.active {{ color:var(--primary); border-bottom-color:var(--primary); }}
 .panel {{ display:none; }}
 .panel.active {{ display:block; }}
 .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:20px; }}
 .card {{ background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:20px; box-shadow:0 1px 2px rgba(15,23,42,.04),0 4px 12px rgba(15,23,42,.06); }}
 .metric-label {{ color:var(--muted); font-size:13px; font-weight:500; margin-bottom:4px; }}
 .metric-value {{ font-size:22px; font-weight:700; }}
 table {{ width:100%; border-collapse:collapse; font-size:13px; }}
 td, th {{ padding:8px 6px; border-bottom:1px solid var(--border); text-align:left; }}
 th {{ color:var(--muted); font-weight:600; }}
 .field {{ margin-right:16px; margin-bottom:12px; display:inline-block; }}
 label {{ display:block; color:var(--muted); font-size:12px; font-weight:500; margin-bottom:4px; }}
 input {{ background:var(--bg); border:1px solid var(--border); color:var(--text); padding:8px 10px; border-radius:8px; width:90px; font-size:14px; }}
 button {{ background:var(--primary); border:none; color:#fff; padding:10px 18px; border-radius:8px; cursor:pointer; font-weight:600; font-size:14px; min-height:44px; box-shadow:0 8px 24px rgba(79,70,229,.25); }}
 pre {{ white-space:pre-wrap; word-break:break-word; color:var(--muted); background:var(--bg); border-radius:8px; padding:12px; margin-top:12px; font-size:12px; }}
</style></head>
<body>
<header>
  <div class="brand"><span class="mark">H</span> {APP_NAME}</div>
  <span class="track">&#9679; {COLOR.upper()} &middot; {APP_VERSION}</span>
</header>
<div class="wrap">
  <div class="tabs" role="tablist">
    <div class="tab active" data-tab="overview" role="tab">Overview</div>
    <div class="tab" data-tab="activity" role="tab">Activity</div>
    <div class="tab" data-tab="performance" role="tab">Performance</div>
    <div class="tab" data-tab="runtime" role="tab">Runtime</div>
  </div>

  <div class="panel active" id="panel-overview">
    <div class="grid">
      <div class="card"><div class="metric-label">Application Health</div><div class="metric-value" id="ov-health">—</div></div>
      <div class="card"><div class="metric-label">Version</div><div class="metric-value">{APP_VERSION}</div></div>
      <div class="card"><div class="metric-label">Requests</div><div class="metric-value" id="ov-requests">—</div></div>
      <div class="card"><div class="metric-label">Avg Latency</div><div class="metric-value" id="ov-latency">—</div></div>
    </div>
    <p style="color:var(--muted); font-size:13px;">Cluster-wide figures (replica count, traffic split) are shown in the HKS Experience portal, which can see across pods — this page only reports what this single pod genuinely knows about itself.</p>
  </div>

  <div class="panel" id="panel-activity">
    <div class="card">
      <table>
        <thead><tr><th>Time</th><th>Method</th><th>Path</th><th>Status</th><th>Duration</th></tr></thead>
        <tbody id="activity-rows"><tr><td colspan="5">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="panel" id="panel-performance">
    <div class="grid">
      <div class="card"><div class="metric-label">CPU (user+sys)</div><div class="metric-value" id="perf-cpu">—</div></div>
      <div class="card"><div class="metric-label">Peak Memory</div><div class="metric-value" id="perf-mem">—</div></div>
      <div class="card"><div class="metric-label">Active CPU Jobs</div><div class="metric-value" id="perf-cpujobs">—</div></div>
      <div class="card"><div class="metric-label">Active Memory Jobs</div><div class="metric-value" id="perf-memjobs">—</div></div>
    </div>
    <div class="card">
      <h3 style="margin-top:0">Workload Generator</h3>
      <p style="color:var(--muted); font-size:13px;">Safe limits enforced server-side (memory capped at 512MB, duration capped at 300s).</p>
      <div class="field"><label>CPU load %</label><input id="cpu" type="number" value="70" min="0" max="100"></div>
      <div class="field"><label>Duration (s)</label><input id="dur" type="number" value="60" min="1" max="300"></div>
      <div class="field"><label>Concurrency</label><input id="conc" type="number" value="4" min="1" max="8"></div>
      <br><button onclick="startCpu()">Start CPU Load</button>
      <hr style="border:none; border-top:1px solid var(--border); margin:16px 0">
      <div class="field"><label>Memory (MB)</label><input id="mem" type="number" value="128" min="1" max="512"></div>
      <div class="field"><label>Duration (s)</label><input id="memdur" type="number" value="60" min="1" max="300"></div>
      <br><button onclick="startMem()">Start Memory Load</button>
      <pre id="out"></pre>
    </div>
  </div>

  <div class="panel" id="panel-runtime">
    <div class="card">
      <table>
        <tr><td>Pod</td><td>{POD_NAME}</td></tr>
        <tr><td>Node</td><td>{NODE_NAME}</td></tr>
        <tr><td>Namespace</td><td>{NAMESPACE}</td></tr>
        <tr><td>Container</td><td>{CONTAINER_NAME}</td></tr>
        <tr><td>Uptime (s)</td><td>{uptime}</td></tr>
      </table>
    </div>
  </div>
</div>
<script>
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {{
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById('panel-' + t.dataset.tab).classList.add('active');
}}));

function startCpu() {{
  const cpu = document.getElementById('cpu').value, dur = document.getElementById('dur').value, conc = document.getElementById('conc').value;
  fetch('/api/load?cpu=' + cpu + '&duration=' + dur + '&concurrency=' + conc, {{method:'POST'}})
    .then(r => r.json()).then(d => document.getElementById('out').textContent = JSON.stringify(d, null, 2));
}}
function startMem() {{
  const mb = document.getElementById('mem').value, dur = document.getElementById('memdur').value;
  fetch('/api/load/memory?mb=' + mb + '&duration=' + dur, {{method:'POST'}})
    .then(r => r.json()).then(d => document.getElementById('out').textContent = JSON.stringify(d, null, 2));
}}
function poll() {{
  fetch('/api/info').then(r => r.json()).then(d => {{
    document.getElementById('ov-health').textContent = d.health;
    document.getElementById('ov-requests').textContent = d.request_count;
    document.getElementById('ov-latency').textContent = d.avg_latency_ms + ' ms';
    document.getElementById('perf-cpu').textContent = d.resource_usage.cpu_user_seconds + 's';
    document.getElementById('perf-mem').textContent = Math.round(d.resource_usage.max_rss_kb / 1024) + ' MB';
    document.getElementById('perf-cpujobs').textContent = d.active_cpu_jobs;
    document.getElementById('perf-memjobs').textContent = d.active_memory_jobs;
    const rows = d.recent_requests.slice().reverse().map(r =>
      `<tr><td>${{r.time.split('T')[1].split('.')[0]}}</td><td>${{r.method}}</td><td>${{r.path}}</td><td>${{r.status}}</td><td>${{r.duration_ms}}ms</td></tr>`
    ).join('');
    document.getElementById('activity-rows').innerHTML = rows || '<tr><td colspan="5">No requests yet</td></tr>';
  }}).catch(function(){{}});
}}
poll();
setInterval(poll, 3000);
</script>
</body></html>"""


def metrics_text():
    usage = real_resource_usage()
    with STATE_LOCK:
        req_count = STATE["request_count"]
    lines = [
        "# HELP app_info Static application info",
        "# TYPE app_info gauge",
        f'app_info{{version="{APP_VERSION}",color="{COLOR}",pod="{POD_NAME}",node="{NODE_NAME}",namespace="{NAMESPACE}"}} 1',
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
        f"http_requests_total {req_count}",
        "# HELP process_cpu_seconds_total Real CPU time consumed by this process",
        "# TYPE process_cpu_seconds_total counter",
        f'process_cpu_seconds_total {usage["cpu_user_seconds"] + usage["cpu_system_seconds"]}',
        "# HELP process_max_rss_bytes Real peak resident memory",
        "# TYPE process_max_rss_bytes gauge",
        f'process_max_rss_bytes {usage["max_rss_kb"] * 1024}',
    ]
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    server_version = "hks-demo-workload/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        t0 = time.time()
        parsed = urlparse(self.path)
        path = parsed.path
        status = 200
        if path == "/":
            self._send(200, render_index(), "text/html")
        elif path == "/healthz":
            self._send(200, json.dumps({"status": "ok"}))
        elif path == "/readyz":
            with STATE_LOCK:
                fail_until = STATE["readiness_fail_until"]
            if time.time() < fail_until:
                status = 503
                self._send(503, json.dumps({"status": "not-ready"}))
            else:
                self._send(200, json.dumps({"status": "ready"}))
        elif path == "/livez":
            with STATE_LOCK:
                fail_until = STATE["liveness_fail_until"]
            if time.time() < fail_until:
                status = 500
                self._send(500, json.dumps({"status": "unhealthy"}))
            else:
                self._send(200, json.dumps({"status": "alive"}))
        elif path == "/api/info":
            with STATE_LOCK:
                req_count = STATE["request_count"]
                recent = list(STATE["recent_requests"])
                active_cpu = STATE["active_cpu_jobs"]
                active_mem = STATE["active_memory_jobs"]
                ready = time.time() >= STATE["readiness_fail_until"]
                alive = time.time() >= STATE["liveness_fail_until"]
            durations = [r["duration_ms"] for r in recent] or [0]
            self._send(200, json.dumps({
                "application": APP_NAME,
                "version": APP_VERSION,
                "color": COLOR,
                "pod": POD_NAME,
                "node": NODE_NAME,
                "namespace": NAMESPACE,
                "container": CONTAINER_NAME,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": round(time.time() - START_TIME, 1),
                "health": "Healthy" if (ready and alive) else ("Not Ready" if not ready else "Unhealthy"),
                "request_count": req_count,
                "avg_latency_ms": round(sum(durations) / len(durations), 2),
                "active_cpu_jobs": active_cpu,
                "active_memory_jobs": active_mem,
                "recent_requests": recent,
                "resource_usage": real_resource_usage(),
                "request_id": str(uuid.uuid4()),
            }))
        elif path == "/metrics":
            self._send(200, metrics_text(), "text/plain; version=0.0.4")
        else:
            status = 404
            self._send(404, json.dumps({"error": "not found"}))
        record_request("GET", path, status, time.time() - t0)

    def do_POST(self):
        t0 = time.time()
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        status = 200
        if path == "/api/load":
            cpu = int(qs.get("cpu", ["50"])[0])
            duration = max(1, min(int(qs.get("duration", ["30"])[0]), 300))
            concurrency = max(1, min(int(qs.get("concurrency", ["1"])[0]), 8))
            start_cpu_load(cpu, duration, concurrency)
            self._send(200, json.dumps({"started": True, "type": "cpu", "cpu_pct": cpu, "duration_s": duration, "concurrency": concurrency}))
        elif path == "/api/load/memory":
            mb = int(qs.get("mb", ["128"])[0])
            duration = int(qs.get("duration", ["60"])[0])
            start_memory_load(mb, duration)
            self._send(200, json.dumps({"started": True, "type": "memory", "mb": min(mb, 512), "duration_s": min(duration, 300)}))
        elif path == "/api/chaos/readiness-fail":
            seconds = int(qs.get("seconds", ["30"])[0])
            with STATE_LOCK:
                STATE["readiness_fail_until"] = time.time() + seconds
            self._send(200, json.dumps({"readiness_fail_seconds": seconds}))
        elif path == "/api/chaos/liveness-fail":
            seconds = int(qs.get("seconds", ["30"])[0])
            with STATE_LOCK:
                STATE["liveness_fail_until"] = time.time() + seconds
            self._send(200, json.dumps({"liveness_fail_seconds": seconds}))
        else:
            status = 404
            self._send(404, json.dumps({"error": "not found"}))
        record_request("POST", path, status, time.time() - t0)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"{APP_NAME} {APP_VERSION} ({COLOR}) listening on :{PORT}, pod={POD_NAME} node={NODE_NAME} ns={NAMESPACE}")
    server.serve_forever()
