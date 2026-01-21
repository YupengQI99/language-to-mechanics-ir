import pytest

from lang2mech_ir import MechanicsIR, MechanicsAuditor


def test_auditor_resolves_geometry_and_speed_conflicts():
    ir = MechanicsIR()
    ir.peg.radius_m = 0.006
    ir.hole.radius_m = 0.005
    ir.max_force.maximum = 4.0
    ir.trajectory.insertion_speed_mps = 0.08
    ir.materials.friction_coefficient = 1.5

    auditor = MechanicsAuditor(min_clearance_m=2e-4)
    result = auditor.audit(ir)

    assert result.valid is True
    corrected = result.corrected_ir
    assert corrected.hole.radius_m - corrected.peg.radius_m == pytest.approx(2e-4)
    assert corrected.tolerances.clearance_m == pytest.approx(2e-4)
    assert corrected.trajectory.insertion_speed_mps == pytest.approx(auditor.conservative_speed_mps)
    assert corrected.materials.friction_coefficient == pytest.approx(0.3)
    assert any("clearance" in note for note in result.observations)


def test_auditor_handles_force_bounds_and_tolerances():
    ir = MechanicsIR()
    ir.max_force.maximum = 2.0
    ir.max_force.minimum = 5.0
    ir.tolerances.alignment_deg = 9.0
    ir.tolerances.position_m = -0.001

    result = MechanicsAuditor().audit(ir)

    assert result.corrected_ir.max_force.maximum == pytest.approx(2.0)
    assert result.corrected_ir.max_force.minimum is None
    assert result.corrected_ir.tolerances.alignment_deg <= 5.0
    assert result.corrected_ir.tolerances.position_m == pytest.approx(5e-4)
