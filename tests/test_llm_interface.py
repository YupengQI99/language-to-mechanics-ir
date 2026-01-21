import pytest

from lang2mech_ir.llm_interface import LLMInterface


def test_llm_interface_extracts_geometry_and_limits():
    interface = LLMInterface()
    instruction = (
        "Slowly insert the 10 mm peg that is 100 mm long into the 10.6 mm hole "
        "which is 40 mm deep, using no more than 5 N of force and finish in 5 seconds "
        "while keeping alignment under 1 deg."
    )

    ir = interface.compile(instruction)

    assert ir.peg.radius_m == pytest.approx(0.005)
    assert ir.peg.length_m == pytest.approx(0.1)
    assert ir.hole.radius_m == pytest.approx(0.0053)
    assert ir.hole.depth_m == pytest.approx(0.04)
    assert ir.max_force.maximum == pytest.approx(5.0)
    assert ir.time_limit_s == pytest.approx(5.0)
    assert ir.tolerances.alignment_deg == pytest.approx(1.0)
    assert ir.trajectory.insertion_speed_mps == pytest.approx(0.002)


def test_llm_interface_detects_strategy_and_speeds():
    interface = LLMInterface()
    instruction = (
        "Perform a spiral search, approach at 0.2 cm/s, retract at 5 mm/s, and maintain a clearance of 0.05 mm "
        "while completing the move within 8 seconds."
    )

    ir = interface.compile(instruction)

    assert ir.trajectory.strategy == "spiral_search"
    assert ir.trajectory.approach_speed_mps == pytest.approx(0.002)
    assert ir.trajectory.retraction_speed_mps == pytest.approx(0.005)
    assert ir.tolerances.clearance_m == pytest.approx(0.00005)
    assert ir.time_limit_s == pytest.approx(8.0)
