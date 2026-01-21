import pytest

from lang2mech_ir import units


def test_length_conversion_and_assumption():
    explicit = units.length_to_m("5 mm")
    assert explicit.unit == "m"
    assert explicit.value == pytest.approx(0.005)
    assert explicit.assumed_unit is False

    assumed = units.length_to_m(0.01)
    assert assumed.value == pytest.approx(0.01)
    assert assumed.assumed_unit is True


def test_force_speed_and_time_conversion():
    force = units.force_to_newtons("0.5 kN")
    assert force.value == pytest.approx(500.0)

    speed = units.speed_to_mps("20 mm/s")
    assert speed.value == pytest.approx(0.02)

    duration = units.time_to_seconds("2.5 min")
    assert duration.value == pytest.approx(150.0)


def test_angle_and_acceleration_conversion():
    angle = units.angle_to_deg("3.14159 rad")
    assert angle.value == pytest.approx(180.0, rel=1e-4)

    gravity = units.acceleration_to_mps2("981 cm/s^2")
    assert gravity.value == pytest.approx(9.81)
