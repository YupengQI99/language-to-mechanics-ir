"""Lightweight simulation harness for one-dimensional peg insertion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..ir_schema import MechanicsIR
from ..controller import PegInHoleState, ControllerConfig, PegInHoleMPC


@dataclass
class SimulationConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    max_time_s: float = 10.0
    contact_spring: float = 10000.0
    contact_damping: float = 200.0


@dataclass
class EpisodeLog:
    times_s: List[float] = field(default_factory=list)
    positions_m: List[float] = field(default_factory=list)
    velocities_mps: List[float] = field(default_factory=list)
    controls_mps2: List[float] = field(default_factory=list)
    contact_forces_N: List[float] = field(default_factory=list)

    def append(self, t: float, state: PegInHoleState, control: float, contact_force: float) -> None:
        self.times_s.append(t)
        self.positions_m.append(state.position_m)
        self.velocities_mps.append(state.velocity_mps)
        self.controls_mps2.append(control)
        self.contact_forces_N.append(contact_force)


@dataclass
class SimpleInsertionSimulator:
    """Integrates the 1-D dynamics and logs interaction forces."""

    config: SimulationConfig = field(default_factory=SimulationConfig)

    def run_episode(self, ir: MechanicsIR, initial_state: PegInHoleState) -> EpisodeLog:
        controller = PegInHoleMPC(self.config.controller)
        state = PegInHoleState(
            position_m=initial_state.position_m,
            velocity_mps=initial_state.velocity_mps,
            depth_goal_m=initial_state.depth_goal_m,
            timestamp_s=initial_state.timestamp_s,
        )
        log = EpisodeLog()
        dt = self.config.controller.timestep_s
        t = state.timestamp_s
        goal = ir.hole.depth_m
        mass = self.config.controller.mass_kg

        while t <= self.config.max_time_s:
            control = controller.compute_control(ir, state)
            # Integrate dynamics (simple Euler step)
            state.velocity_mps += dt * control
            state.position_m += dt * state.velocity_mps

            penetration = max(0.0, state.position_m - goal)
            contact_force = self.config.contact_spring * penetration + self.config.contact_damping * max(0.0, state.velocity_mps)
            if contact_force > ir.max_force.maximum:
                contact_force = ir.max_force.maximum
                # reflect excessive penetration
                state.position_m = goal + contact_force / self.config.contact_spring

            t += dt
            state.timestamp_s = t
            log.append(t, state, control, contact_force)

            if penetration <= 1e-4 and abs(state.position_m - goal) < 1e-3 and abs(state.velocity_mps) < 1e-3:
                break

        return log
