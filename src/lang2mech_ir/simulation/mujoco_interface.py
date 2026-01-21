"""MuJoCo interface scaffolding for the peg-in-hole controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from ..controller import PegInHoleState, JointSpaceState


try:  # pragma: no cover - optional dependency
    import mujoco
except ImportError:  # pragma: no cover - optional dependency
    mujoco = None


@dataclass
class MujocoPegInHoleConfig:
    model_path: Path
    sim_timestep_s: float = 0.001
    control_timestep_s: float = 0.02
    enable_render: bool = False
    joint_names: Sequence[str] = field(default_factory=lambda: ["slide_z"])
    actuator_names: Sequence[str] = field(default_factory=lambda: ["slide_motor"])


class MujocoPegInHoleEnv:
    """Minimal facade around MuJoCo's C API/`mujoco` Python bindings."""

    def __init__(self, config: MujocoPegInHoleConfig) -> None:
        if mujoco is None:
            raise RuntimeError("MuJoCo python bindings are not installed. Please `pip install mujoco`.")
        self.config = config
        self.model = mujoco.MjModel.from_xml_path(str(config.model_path))
        self.data = mujoco.MjData(self.model)
        self.renderer = None
        if config.enable_render:
            self.renderer = mujoco.Renderer(self.model)
        self.control_counter = 0
        self.control_interval = max(1, int(config.control_timestep_s / config.sim_timestep_s))
        self.joint_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in config.joint_names
        ]
        self.actuator_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            for name in config.actuator_names
        ]
        if len(self.joint_ids) != len(self.actuator_ids):
            raise ValueError("joint_names and actuator_names must have the same length")
        self._goal_positions = [0.0] * len(self.joint_ids)

    def reset(self, goal_positions: Optional[Sequence[float]] = None) -> JointSpaceState:
        mujoco.mj_resetData(self.model, self.data)
        self.control_counter = 0
        if goal_positions is not None:
            if len(goal_positions) != len(self.joint_ids):
                raise ValueError("goal_positions must match joint count")
            self._goal_positions = list(goal_positions)
        return self.get_joint_state()

    def step(self, control_input, state_estimate: Optional[JointSpaceState] = None) -> JointSpaceState:
        if control_input is None:
            controls = [0.0] * len(self.actuator_ids)
        elif isinstance(control_input, (list, tuple)):
            controls = control_input
        else:
            controls = [float(control_input)] * len(self.actuator_ids)
        if len(controls) != len(self.actuator_ids):
            raise ValueError("Control dimension must match actuator count")
        for aid, ctrl in zip(self.actuator_ids, controls):
            self.data.ctrl[aid] = ctrl
        steps = self.control_interval
        for _ in range(steps):
            mujoco.mj_step(self.model, self.data)
        self.control_counter += 1
        return self.get_joint_state()

    def render(self) -> bytes | None:  # pragma: no cover - requires GL context
        if not self.renderer:
            return None
        self.renderer.update_scene(self.data)
        return self.renderer.render()

    def set_goal_positions(self, goals: Sequence[float]) -> None:
        if len(goals) != len(self.joint_ids):
            raise ValueError("goal_positions must match joint count")
        self._goal_positions = list(goals)

    def get_contact_force(self) -> float:
        mujoco.mj_rnePostConstraint(self.model, self.data)
        if not self.joint_ids:
            return 0.0
        return float(abs(self.data.qfrc_constraint[self.joint_ids[-1]]))

    def get_joint_state(self) -> JointSpaceState:
        positions = [float(self.data.qpos[j]) for j in self.joint_ids]
        velocities = [float(self.data.qvel[j]) for j in self.joint_ids]
        sim_time = float(self.data.time)
        return JointSpaceState(joint_positions=positions, joint_velocities=velocities, goal_positions=self._goal_positions, timestamp_s=sim_time)
