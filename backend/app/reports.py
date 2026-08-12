"""Report generation. IMPORTANT: this reports on the *recorded* results in
tests/definitions/*.yaml (each carrying its own last_validated date) -- it
does not re-run anything against a live cluster. A report generated here
reflects "what was last validated and recorded," not "what just happened."
Live test execution (tests/validation/) is a separate concern.
"""
from datetime import datetime, timezone
from typing import Any

from . import definitions, k8s
from .matrix import build_matrix


def build_report() -> dict[str, Any]:
    cluster = k8s.discover_cluster()
    all_defs = definitions.load_all()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_title": "HKS Capability Validation Report",
        "cluster": {
            "connected": cluster.connected,
            "context": cluster.context,
            "kubernetes_version": cluster.kubernetes_version,
            "node_count": cluster.node_count,
        },
        "summary": definitions.summary_counts(),
        "total_definitions": len(all_defs),
        "matrix": build_matrix(),
        "categories": definitions.by_category(),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['report_title']}", "", f"Generated: {report['generated_at']}", ""]
    cluster = report["cluster"]
    lines.append("## Cluster")
    if cluster["connected"]:
        lines.append(f"- Context: `{cluster['context']}`")
        lines.append(f"- Kubernetes version: {cluster['kubernetes_version']}")
        lines.append(f"- Nodes: {cluster['node_count']}")
    else:
        lines.append("- Not connected (report reflects recorded results only)")
    lines.append("")
    lines.append("## Summary")
    for result, count in sorted(report["summary"].items()):
        lines.append(f"- **{result}**: {count}")
    lines.append("")
    lines.append("## Capability Matrix")
    lines.append("")
    lines.append("| ID | Capability | Category | YAML | Helm | Result |")
    lines.append("|---|---|---|---|---|---|")
    for row in report["matrix"]:
        yaml_mark = "✓" if row["yaml"] else "—"
        helm_mark = "✓" if row["helm"] else "—"
        lines.append(
            f"| {row['id']} | {row['name']} | {row['category']} | "
            f"{yaml_mark} | {helm_mark} | {row['result']} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    result_class = {
        "PASS": "pass",
        "FAIL": "fail",
        "NOT_AVAILABLE": "na",
        "NOT_VALIDATED": "nv",
        "NOT_APPLICABLE": "na",
        "BLOCKED": "blocked",
        "NOT_TESTED": "nt",
    }
    rows_html = []
    for row in report["matrix"]:
        cls = result_class.get(row["result"], "nt")
        yaml_mark = "&#10003; YAML" if row["yaml"] else "&#8212;"
        helm_mark = "&#10003; Helm" if row["helm"] else "&#8212;"
        rows_html.append(
            f"<tr><td>{row['id']}</td><td>{row['name']}</td><td>{row['category']}</td>"
            f"<td>{yaml_mark}</td><td>{helm_mark}</td>"
            f"<td class='result {cls}'>{row['result']}</td></tr>"
        )
    cluster = report["cluster"]
    cluster_html = (
        f"Context <b>{cluster['context']}</b> &middot; Kubernetes {cluster['kubernetes_version']} "
        f"&middot; {cluster['node_count']} nodes"
        if cluster["connected"]
        else "Not connected &mdash; report reflects recorded results only"
    )
    summary_html = "".join(
        f"<span class='chip {result_class.get(r, 'nt')}'>{r}: {c}</span>"
        for r, c in sorted(report["summary"].items())
        if c
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{report['report_title']}</title>
<style>
:root {{ --bg:#F8FAFC; --surface:#FFFFFF; --primary:#4F46E5; --text:#0F172A; --muted:#64748B; --success:#10B981; --border:#E2E8F0; }}
body {{ font-family: 'Plus Jakarta Sans', -apple-system, Segoe UI, Roboto, sans-serif; background:var(--bg); color:var(--text); margin:0; padding:40px; }}
h1 {{ font-weight:800; }}
.meta {{ color:var(--muted); margin-bottom:24px; }}
table {{ width:100%; border-collapse:collapse; background:var(--surface); border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(15,23,42,0.08); }}
th,td {{ padding:10px 14px; border-bottom:1px solid var(--border); text-align:left; font-size:14px; }}
th {{ background:#EEF2FF; color:var(--primary); font-weight:600; }}
.chip {{ display:inline-block; padding:4px 10px; border-radius:999px; margin-right:8px; font-size:12px; font-weight:600; }}
.chip.pass {{ background:#D1FAE5; color:#065F46; }}
.chip.na, .chip.nv {{ background:#FEF3C7; color:#92400E; }}
.chip.fail {{ background:#FEE2E2; color:#991B1B; }}
.chip.nt, .chip.blocked {{ background:#E2E8F0; color:#334155; }}
td.result.pass {{ color:#065F46; font-weight:600; }}
td.result.na, td.result.nv {{ color:#92400E; font-weight:600; }}
td.result.fail {{ color:#991B1B; font-weight:600; }}
</style></head>
<body>
<h1>{report['report_title']}</h1>
<div class="meta">Generated {report['generated_at']} &middot; {cluster_html}</div>
<div style="margin-bottom:20px">{summary_html}</div>
<table>
<tr><th>ID</th><th>Capability</th><th>Category</th><th>YAML</th><th>Helm</th><th>Result</th></tr>
{''.join(rows_html)}
</table>
</body></html>"""
