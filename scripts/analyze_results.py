"""Aggregate metrics from 1D and Panda experiment JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Iterable

RESULT_FILES = [
    Path("results/language_pipeline.json"),
    Path("results/panda_pipeline.json"),
    Path("results/panda_full_batch.json"),
]


def load_entries(path: Path) -> list:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_metric(entry: dict) -> dict:
    if "metrics_1d" in entry:
        return entry["metrics_1d"]
    if "metrics" in entry:
        return entry["metrics"]
    return {
        "success": entry.get("success", False),
        "final_depth_m": entry.get("final_depth_m", 0.0),
        "goal_depth_m": entry.get("goal_depth_m", 0.0),
    }


def summarize(entries: Iterable[dict]) -> dict:
    entries = list(entries)
    if not entries:
        return {}
    metrics = [_extract_metric(e) for e in entries]
    success_rate = mean(1.0 if m.get("success", False) else 0.0 for m in metrics)
    depth_errors = [abs(m.get("goal_depth_m", 0.0) - m.get("final_depth_m", 0.0)) for m in metrics]
    panda_depths = [e.get("panda_final_depth_m") for e in entries if e.get("panda_final_depth_m") is not None]
    panda_forces = [e.get("panda_final_force_N") for e in entries if e.get("panda_final_force_N") is not None]
    return {
        "count": len(entries),
        "success_rate_1d": success_rate,
        "avg_depth_error_1d": mean(depth_errors),
        "avg_panda_depth": mean(p for p in panda_depths) if panda_depths else None,
        "avg_panda_force": mean(p for p in panda_forces) if panda_forces else None,
    }


def main() -> None:
    summary = {}
    for result_file in RESULT_FILES:
        entries = load_entries(result_file)
        if not entries:
            continue
        summary[result_file.name] = summarize(entries)

    out_path = Path("results/summary.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote aggregate metrics to {out_path}")
    for name, stats in summary.items():
        print(name, stats)


if __name__ == "__main__":
    main()
