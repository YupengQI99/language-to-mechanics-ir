"""Shared dataclasses for MPC controller state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PegInHoleState:
    """Simplified peg-in-hole state in the insertion axis."""

    position_m: float
    velocity_mps: float
    depth_goal_m: float
    timestamp_s: float = 0.0


@dataclass
class ControllerConfig:
    """Tunable MPC parameters."""

    horizon: int = 10
    timestep_s: float = 0.02
    mass_kg: float = 2.0
    spring_k: float = 10000.0  # soft contact stiffness
    damping: float = 50.0
    position_weight: float = 50.0
    velocity_weight: float = 5.0
    control_weight: float = 0.1
    force_slack_weight: float = 500.0
    velocity_limit_mps: float = 0.1
    acceleration_limit_mps2: float = 2.0
    contact_start_depth_m: float = 0.0


@dataclass
class MPCPlan:
    """Result of one MPC optimization."""

    control_sequence: List[float] = field(default_factory=list)
    predicted_positions: List[float] = field(default_factory=list)
    predicted_velocities: List[float] = field(default_factory=list)
    cost: float | None = None

    def first_control(self) -> float:
        return self.control_sequence[0] if self.control_sequence else 0.0


@dataclass
class JointSpaceState:
    """Joint-space state for multi-DoF controllers."""

    joint_positions: List[float]
    joint_velocities: List[float]
    goal_positions: List[float]
    timestamp_s: float = 0.0


@dataclass
class MultiJointMPCPlan:
    """Plan for multiple joints (contains per-joint control sequences)."""

    control_sequences: List[List[float]] = field(default_factory=list)
    costs: List[float | None] = field(default_factory=list)

    def first_controls(self) -> List[float]:
        return [seq[0] if seq else 0.0 for seq in self.control_sequences]
