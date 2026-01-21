"""Episode-level metrics inspired by Section 7 of the research plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..ir_schema import MechanicsIR
from ..simulation.environment import EpisodeLog


@dataclass
class EpisodeMetrics:
    success: bool
    final_depth_m: float
    goal_depth_m: float
    final_force_N: float
    force_violation: bool
    max_force_N: float
    duration_s: float

    def as_dict(self) -> Dict[str, float | bool]:  # pragma: no cover - simple serialization
        return {
            "success": self.success,
            "final_depth_m": self.final_depth_m,
            "goal_depth_m": self.goal_depth_m,
            "final_force_N": self.final_force_N,
            "force_violation": self.force_violation,
            "max_force_N": self.max_force_N,
            "duration_s": self.duration_s,
        }


def compute_metrics(ir: MechanicsIR, log: EpisodeLog, depth_tolerance: float = 1e-3) -> EpisodeMetrics:
    if not log.times_s:
        return EpisodeMetrics(
            success=False,
            final_depth_m=0.0,
            goal_depth_m=ir.hole.depth_m,
            final_force_N=0.0,
            force_violation=False,
            max_force_N=0.0,
            duration_s=0.0,
        )

    final_depth = log.positions_m[-1]
    final_force = log.contact_forces_N[-1]
    max_force_observed = max(log.contact_forces_N) if log.contact_forces_N else 0.0
    goal = ir.hole.depth_m
    duration = log.times_s[-1]
    success = (final_depth >= goal - depth_tolerance) and (max_force_observed <= ir.max_force.maximum + 1e-6)
    force_violation = max_force_observed > ir.max_force.maximum + 1e-6
    return EpisodeMetrics(
        success=success,
        final_depth_m=final_depth,
        goal_depth_m=goal,
        final_force_N=final_force,
        force_violation=force_violation,
        max_force_N=max_force_observed,
        duration_s=duration,
    )
