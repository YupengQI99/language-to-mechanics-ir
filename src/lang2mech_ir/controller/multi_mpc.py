"""Multi-DoF MPC wrapper that reuses the single-axis controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..ir_schema import MechanicsIR
from .state import JointSpaceState, MultiJointMPCPlan, ControllerConfig, PegInHoleState
from .mpc import PegInHoleMPC


@dataclass
class MultiJointMPCConfig:
    joint_count: int
    horizon: int = 10
    timestep_s: float = 0.02
    masses: List[float] = field(default_factory=list)
    max_forces: List[float] = field(default_factory=list)
    speed_targets: List[float] = field(default_factory=list)
    velocity_limits: List[float] = field(default_factory=list)
    acceleration_limits: List[float] = field(default_factory=list)
    position_weights: List[float] = field(default_factory=list)
    velocity_weights: List[float] = field(default_factory=list)
    control_weights: List[float] = field(default_factory=list)
    slack_weights: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.masses = self._broadcast(self.masses, 2.0)
        self.max_forces = self._broadcast(self.max_forces, 15.0)
        self.speed_targets = self._broadcast(self.speed_targets, 0.02)
        self.velocity_limits = self._broadcast(self.velocity_limits, 0.2)
        self.acceleration_limits = self._broadcast(self.acceleration_limits, 2.0)
        self.position_weights = self._broadcast(self.position_weights, 25.0)
        self.velocity_weights = self._broadcast(self.velocity_weights, 3.0)
        self.control_weights = self._broadcast(self.control_weights, 0.1)
        self.slack_weights = self._broadcast(self.slack_weights, 100.0)

    def _broadcast(self, values: List[float], default: float) -> List[float]:
        if not values:
            return [default] * self.joint_count
        if len(values) != self.joint_count:
            raise ValueError("Config list length must match joint_count")
        return values


class MultiJointMPC:
    """Solve decoupled MPC problems for each joint."""

    def __init__(self, config: MultiJointMPCConfig) -> None:
        self.config = config

    def plan(self, state: JointSpaceState) -> MultiJointMPCPlan:
        controls: List[List[float]] = []
        costs: List[float | None] = []
        for idx in range(self.config.joint_count):
            controller = PegInHoleMPC(self._single_controller_config(idx))
            ir = self._single_ir(idx, state.goal_positions[idx])
            joint_state = PegInHoleState(
                position_m=state.joint_positions[idx],
                velocity_mps=state.joint_velocities[idx],
                depth_goal_m=state.goal_positions[idx],
                timestamp_s=state.timestamp_s,
            )
            plan = controller.plan(ir, joint_state)
            controls.append(plan.control_sequence)
            costs.append(plan.cost)
        return MultiJointMPCPlan(control_sequences=controls, costs=costs)

    def _single_controller_config(self, idx: int) -> ControllerConfig:
        return ControllerConfig(
            horizon=self.config.horizon,
            timestep_s=self.config.timestep_s,
            mass_kg=self.config.masses[idx],
            position_weight=self.config.position_weights[idx],
            velocity_weight=self.config.velocity_weights[idx],
            control_weight=self.config.control_weights[idx],
            force_slack_weight=self.config.slack_weights[idx],
            velocity_limit_mps=self.config.velocity_limits[idx],
            acceleration_limit_mps2=self.config.acceleration_limits[idx],
        )

    def _single_ir(self, idx: int, goal: float) -> MechanicsIR:
        ir = MechanicsIR()
        ir.hole.depth_m = goal
        ir.max_force.maximum = self.config.max_forces[idx]
        ir.trajectory.insertion_speed_mps = self.config.speed_targets[idx]
        return ir
