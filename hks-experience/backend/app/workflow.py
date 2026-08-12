"""Loads workflows/*.yaml -- the guided journey's content. Read-only; never
mutates. See workflows/README.md for the schema."""
import glob
import os
from functools import lru_cache
from typing import Any

import yaml

from . import config, public_artifacts


def _hydrate_yaml_deploy(entry: dict[str, Any]) -> None:
    """A step's deploy.yaml.artifact is a public_artifacts id (e.g.
    "namespace"), not a raw filename -- this resolves it against
    ../../yaml/ live, so the actual manifest content/resources/raw URL
    shown in the UI can never drift from what's committed there. Extra
    `commands` in the workflow file (if any) are kubectl-only follow-ups
    beyond the apply itself (e.g. `rollout status`, a selector patch) --
    never envsubst/kubectl-create pipelines."""
    deploy = entry.get("deploy")
    if not deploy or not deploy.get("yaml"):
        return
    artifact_id = deploy["yaml"].get("artifact")
    if not artifact_id:
        return
    artifact = public_artifacts.get(artifact_id)
    if not artifact:
        raise ValueError(f"step '{entry['id']}': unknown public artifact id '{artifact_id}'")
    deploy["yaml"] = {**deploy["yaml"], **artifact.to_dict()}


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
            _hydrate_yaml_deploy(entry)
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
