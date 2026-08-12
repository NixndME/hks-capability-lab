"""Loads workflows/*.yaml -- the guided journey's content. Read-only; never
mutates. See workflows/README.md for the schema."""
import glob
import os
from functools import lru_cache
from typing import Any

import yaml

from . import config


@lru_cache(maxsize=1)
def load_steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(glob.glob(os.path.join(config.WORKFLOWS_DIR, "*.yaml"))):
        data = yaml.safe_load(open(path, encoding="utf-8")) or []
        for entry in data:
            step_id = entry["id"]
            if step_id in seen_ids:
                raise ValueError(f"{path}: duplicate step id '{step_id}'")
            seen_ids.add(step_id)
            steps.append(entry)
    return sorted(steps, key=lambda s: s["order"])


def get_step(step_id: str) -> dict[str, Any] | None:
    for step in load_steps():
        if step["id"] == step_id:
            return step
    return None


def categories() -> list[str]:
    seen = []
    for step in load_steps():
        if step["category"] not in seen:
            seen.append(step["category"])
    return seen


def prerequisites_met(step_id: str, completed_or_skipped: set[str]) -> bool:
    step = get_step(step_id)
    if not step:
        return False
    return all(p in completed_or_skipped for p in step.get("prerequisites", []))
