import pytest

from lang2mech_ir import InstructionParser


def test_parser_normalizes_units_and_defaults():
    parser = InstructionParser()
    payload = {
        "action_type": "peg_in_hole_insertion",
        "peg_dimensions": {
            "radius": "5 mm",
            "length": 0.12,
            "chamfer_angle": "2 deg",
        },
        "hole_dimensions": {
            "diameter": "11 mm",
            "depth": "4 cm",
            "chamfer_angle": "4 deg",
        },
        "material_properties": {
            "friction_coefficient": 0.25,
            "lubrication": True,
            "peg_material": "steel",
            "hole_material": "aluminum",
        },
        "speed": "2 mm/s",
        "trajectory": {
            "approach_speed": "10 mm/s",
            "retraction_speed": "5 mm/s",
            "strategy": "spiral_search",
            "approach_angle": "5 deg",
        },
        "alignment_tolerance": "1.5 deg",
        "position_tolerance": "0.3 mm",
        "clearance": "0.1 mm",
        "max_force": {"maximum": "5 N", "minimum": "1 N"},
        "time_limit": "2 min",
        "environment": {"gravity": "981 cm/s^2", "temperature": 26},
    }

    ir = parser.parse(payload)

    assert ir.peg.radius_m == pytest.approx(0.005)
    assert ir.peg.length_m == pytest.approx(0.12)
    assert ir.hole.radius_m == pytest.approx(0.0055)
    assert ir.hole.depth_m == pytest.approx(0.04)
    assert ir.materials.friction_coefficient == pytest.approx(0.25)
    assert ir.materials.lubrication is True
    assert ir.trajectory.insertion_speed_mps == pytest.approx(0.002)
    assert ir.trajectory.approach_speed_mps == pytest.approx(0.01)
    assert ir.trajectory.retraction_speed_mps == pytest.approx(0.005)
    assert ir.trajectory.strategy == "spiral_search"
    assert ir.tolerances.alignment_deg == pytest.approx(1.5)
    assert ir.tolerances.position_m == pytest.approx(0.0003)
    assert ir.tolerances.clearance_m == pytest.approx(0.0001)
    assert ir.max_force.maximum == pytest.approx(5.0)
    assert ir.max_force.minimum == pytest.approx(1.0)
    assert ir.time_limit_s == pytest.approx(120.0)
    assert ir.environment.gravity_mps2 == pytest.approx(9.81)
    assert ir.environment.temperature_c == pytest.approx(26.0)
    # Notes should mention at least one assumed unit (length in meters by default)
    assert any("peg.length" in note for note in ir.notes)
