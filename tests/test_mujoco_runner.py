import pytest

from pathlib import Path

from lang2mech_ir import MechanicsIR
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

mujoco = pytest.importorskip("mujoco")


def test_run_mujoco_episode_smoke(tmp_path):
    model_path = Path("assets/peg_in_hole.xml").resolve()
    ir = MechanicsIR()
    ir.hole.depth_m = 0.05
    ir.max_force.maximum = 10.0

    log = run_mujoco_episode(ir, model_path, steps=50)
    assert len(log.times_s) > 0
    assert log.positions_m[-1] <= 0.12
