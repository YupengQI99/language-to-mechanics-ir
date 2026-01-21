from lang2mech_ir import MechanicsIR
from lang2mech_ir.logging_utils import compute_metrics
from lang2mech_ir.simulation import EpisodeLog


def make_log(final_depth=0.05, max_force=5.0):
    log = EpisodeLog()
    log.times_s = [0.02, 0.04]
    log.positions_m = [0.02, final_depth]
    log.velocities_mps = [0.1, 0.0]
    log.controls_mps2 = [1.0, 0.0]
    log.contact_forces_N = [2.0, max_force]
    return log


def test_metrics_success_detection():
    ir = MechanicsIR()
    ir.hole.depth_m = 0.05
    ir.max_force.maximum = 5.0
    log = make_log()

    metrics = compute_metrics(ir, log)
    assert metrics.success is True
    assert metrics.force_violation is False


def test_metrics_force_violation():
    ir = MechanicsIR()
    ir.hole.depth_m = 0.05
    ir.max_force.maximum = 3.0
    log = make_log(max_force=4.0)

    metrics = compute_metrics(ir, log)
    assert metrics.success is False
    assert metrics.force_violation is True
