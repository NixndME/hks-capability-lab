"""Loads tests/definitions/*.yaml -- the single source of truth for every
capability this product knows how to describe/validate. See
tests/definitions/README.md for the schema this is trusting.

This module never invents or edits test definitions; it only reads them.
"""
import glob
import os
from functools import lru_cache
from typing import Any

import yaml

from . import config

VALID_RESULTS = {
    "PASS",
    "FAIL",
    "NOT_AVAILABLE",
    "NOT_VALIDATED",
    "NOT_APPLICABLE",
    "BLOCKED",
    "NOT_TESTED",
}


def _load_file(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a top-level YAML list of test definitions")
    return data


@lru_cache(maxsize=1)
def load_all() -> list[dict[str, Any]]:
    """Load and lightly validate every definition. Cached for process lifetime;
    call load_all.cache_clear() if definitions change on disk (e.g. tests)."""
    definitions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    pattern = os.path.join(config.TEST_DEFINITIONS_DIR, "*.yaml")
    for path in sorted(glob.glob(pattern)):
        for entry in _load_file(path):
            test_id = entry.get("id")
            if not test_id:
                raise ValueError(f"{path}: definition missing required 'id' field")
            if test_id in seen_ids:
                raise ValueError(f"{path}: duplicate test id '{test_id}'")
            seen_ids.add(test_id)
            result = entry.get("result")
            if result and result not in VALID_RESULTS:
                raise ValueError(
                    f"{path}: '{test_id}' has invalid result '{result}', "
                    f"expected one of {sorted(VALID_RESULTS)}"
                )
            entry["_source_file"] = os.path.relpath(path, config.REPO_ROOT)
            definitions.append(entry)
    return definitions


def by_category() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in load_all():
        grouped.setdefault(entry.get("category", "Uncategorized"), []).append(entry)
    return grouped


def summary_counts() -> dict[str, int]:
    counts: dict[str, int] = {r: 0 for r in VALID_RESULTS}
    for entry in load_all():
        result = entry.get("result")
        if result in counts:
            counts[result] += 1
    return counts
