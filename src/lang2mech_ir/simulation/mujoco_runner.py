"""Utilities for running MPC inside MuJoCo environments (1-DoF or multi-DoF)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence

from ..controller import (
    PegInHoleState,
    MultiJointMPC,
    MultiJointMPCConfig,
    JointSpaceState,
)
from ..ir_schema import MechanicsIR
from .environment import EpisodeLog
from .mujoco_interface import MujocoPegInHoleConfig, MujocoPegInHoleEnv


def run_mujoco_episode(
    ir: MechanicsIR,
    model_path: Path,
    steps: int = 500,
    *,
    joint_names: Optional[Iterable[str]] = None,
    actuator_names: Optional[Iterable[str]] = None,
    goal_positions: Optional[Sequence[float]] = None,
    multi_config: Optional[MultiJointMPCConfig] = None,
) -> EpisodeLog:
    """Execute MPC inside a MuJoCo model and return the episode log."""

    joint_names = list(joint_names) if joint_names else None
    actuator_names = list(actuator_names) if actuator_names else None
    config = MujocoPegInHoleConfig(
        model_path=model_path,
        joint_names=joint_names or ["slide_z"],
        actuator_names=actuator_names or ["slide_motor"],
    )
    env = MujocoPegInHoleEnv(config)
    joint_count = len(config.joint_names)

    if goal_positions is None:
        goals = [0.0] * joint_count
        goals[-1] = ir.hole.depth_m
    else:
        if len(goal_positions) != joint_count:
            raise ValueError("goal_positions must match joint count")
        goals = list(goal_positions)

    state = env.reset(goals)
    if multi_config is None:
        multi_config = MultiJointMPCConfig(joint_count=joint_count)
    controller = MultiJointMPC(multi_config)
    log = EpisodeLog()

    for _ in range(steps):
        plan = controller.plan(state)
        controls = plan.first_controls()
        state = env.step(controls, state)
        contact_force = env.get_contact_force()
        tip_state = PegInHoleState(
            position_m=state.joint_positions[-1],
            velocity_mps=state.joint_velocities[-1],
            depth_goal_m=state.goal_positions[-1],
            timestamp_s=state.timestamp_s,
        )
        log.append(state.timestamp_s, tip_state, controls[-1], contact_force)
        if abs(tip_state.position_m - tip_state.depth_goal_m) < 1e-3 and abs(tip_state.velocity_mps) < 1e-3:
            break

    return log
