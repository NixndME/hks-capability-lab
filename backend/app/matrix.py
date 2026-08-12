"""Capability matrix: one row per test definition, YAML/Helm deployment-mode
columns driven by each definition's own `deployment_modes` list (never
hard-coded here) -- see tests/definitions/README.md.
"""
from typing import Any

from . import definitions


def build_matrix() -> list[dict[str, Any]]:
    rows = []
    for entry in definitions.load_all():
        modes = entry.get("deployment_modes", [])
        rows.append(
            {
                "id": entry["id"],
                "name": entry.get("name"),
                "category": entry.get("category"),
                "yaml": "yaml" in modes,
                "helm": "helm" in modes,
                "result": entry.get("result", "NOT_TESTED"),
                "result_notes": entry.get("result_notes"),
                "prerequisites": entry.get("prerequisites", []),
                "last_validated": entry.get("last_validated"),
            }
        )
    return sorted(rows, key=lambda r: (r["category"] or "", r["id"]))
