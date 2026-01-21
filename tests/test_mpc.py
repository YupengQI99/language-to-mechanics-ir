import numpy as np

from lang2mech_ir import MechanicsIR
from lang2mech_ir.controller import PegInHoleState, PegInHoleMPC, ControllerConfig


def make_ir(max_force: float = 10.0, insertion_speed: float = 0.01):
    ir = MechanicsIR()
    ir.hole.depth_m = 0.05
    ir.max_force.maximum = max_force
    ir.trajectory.insertion_speed_mps = insertion_speed
    return ir


def test_mpc_respects_force_limit():
    config = ControllerConfig(horizon=5, timestep_s=0.05, mass_kg=2.0)
    controller = PegInHoleMPC(config)
    ir = make_ir(max_force=4.0)
    state = PegInHoleState(position_m=0.0, velocity_mps=0.0, depth_goal_m=ir.hole.depth_m)

    plan = controller.plan(ir, state)
    controls = np.array(plan.control_sequence)
    assert np.all(np.abs(config.mass_kg * controls) <= ir.max_force.maximum + 1e-6)


def test_mpc_tracks_goal_depth():
    controller = PegInHoleMPC()
    ir = make_ir(max_force=20.0)
    state = PegInHoleState(position_m=0.0, velocity_mps=0.0, depth_goal_m=ir.hole.depth_m)

    plan = controller.plan(ir, state)
    assert plan.predicted_positions[-1] > 0.0
    assert plan.predicted_positions[-1] <= ir.hole.depth_m + 1e-3
