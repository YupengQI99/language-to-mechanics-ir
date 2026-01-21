"""Utilities for converting free-form quantities into SI units."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping


_VALUE_RE = re.compile(r"(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(?P<unit>[A-Za-z0-9°/\^]+)?")


def _normalize_unit(token: str) -> str:
    token = token.strip().lower()
    token = token.replace("degrees", "deg").replace("degree", "deg").replace("°", "deg")
    token = token.replace("seconds", "s").replace("second", "s")
    token = token.replace("meters", "m").replace("meter", "m")
    token = token.replace("metres", "m").replace("metre", "m")
    token = token.replace("newtons", "n").replace("newton", "n")
    token = token.replace("per", "/")
    token = token.replace(" ", "")
    return token


@dataclass
class NormalizedValue:
    """A numeric value converted to a canonical unit."""

    value: float
    unit: str
    assumed_unit: bool
    source: Any


class UnitConversionError(ValueError):
    """Raised when a quantity cannot be converted."""


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _extract_amount_and_unit(value: Any) -> tuple[float, str | None]:
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, str):
        match = _VALUE_RE.search(value)
        if not match:
            raise UnitConversionError(f"Could not parse quantity from '{value}'.")
        amount = float(match.group("value"))
        unit = match.group("unit")
        if unit:
            unit = unit.strip()
        else:
            remainder = value[match.end():].strip()
            unit = remainder or None
        return amount, unit
    mapping_value = _as_mapping(value)
    if mapping_value is None:
        raise UnitConversionError(f"Unsupported quantity type: {type(value)!r}")
    if "value" in mapping_value:
        amount = mapping_value["value"]
    elif "amount" in mapping_value:
        amount = mapping_value["amount"]
    else:
        raise UnitConversionError("Mapping must contain 'value' or 'amount'.")
    if amount is None:
        raise UnitConversionError("Quantity is missing a numeric component.")
    unit = mapping_value.get("unit") or mapping_value.get("units")
    if isinstance(unit, str):
        unit = unit.strip()
    elif unit is not None:
        raise UnitConversionError("Unit must be a string if provided.")
    return float(amount), unit


def _convert(value: Any, *, table: Mapping[str, float], default_unit: str, canonical_unit: str) -> NormalizedValue:
    amount, raw_unit = _extract_amount_and_unit(value)
    unit_key = _normalize_unit(raw_unit or default_unit)
    if unit_key not in table:
        raise UnitConversionError(f"Unit '{raw_unit}' is not supported; expected one of {sorted(table)}.")
    return NormalizedValue(
        value=amount * table[unit_key],
        unit=canonical_unit,
        assumed_unit=raw_unit is None,
        source=value,
    )


_LENGTH_UNITS = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "um": 1e-6,
    "in": 0.0254,
    "inch": 0.0254,
}

_SPEED_UNITS = {
    "m/s": 1.0,
    "cm/s": 0.01,
    "mm/s": 0.001,
    "mmps": 0.001,
    "cmps": 0.01,
}

_FORCE_UNITS = {
    "n": 1.0,
    "kn": 1000.0,
    "gf": 0.00980665,
}

_ANGLE_UNITS = {
    "deg": 1.0,
    "rad": 180.0 / math.pi,
}

_TIME_UNITS = {
    "s": 1.0,
    "sec": 1.0,
    "ms": 0.001,
    "us": 1e-6,
    "min": 60.0,
    "minute": 60.0,
    "hr": 3600.0,
    "hour": 3600.0,
}

_ACCEL_UNITS = {
    "m/s^2": 1.0,
    "m/s2": 1.0,
    "cm/s^2": 0.01,
    "cm/s2": 0.01,
    "mm/s^2": 0.001,
    "mm/s2": 0.001,
}


def length_to_m(value: Any, *, default_unit: str = "m") -> NormalizedValue:
    return _convert(value, table=_LENGTH_UNITS, default_unit=default_unit, canonical_unit="m")


def speed_to_mps(value: Any, *, default_unit: str = "m/s") -> NormalizedValue:
    return _convert(value, table=_SPEED_UNITS, default_unit=default_unit, canonical_unit="m/s")


def force_to_newtons(value: Any, *, default_unit: str = "n") -> NormalizedValue:
    return _convert(value, table=_FORCE_UNITS, default_unit=default_unit, canonical_unit="N")


def angle_to_deg(value: Any, *, default_unit: str = "deg") -> NormalizedValue:
    return _convert(value, table=_ANGLE_UNITS, default_unit=default_unit, canonical_unit="deg")


def time_to_seconds(value: Any, *, default_unit: str = "s") -> NormalizedValue:
    return _convert(value, table=_TIME_UNITS, default_unit=default_unit, canonical_unit="s")


def acceleration_to_mps2(value: Any, *, default_unit: str = "m/s^2") -> NormalizedValue:
    return _convert(value, table=_ACCEL_UNITS, default_unit=default_unit, canonical_unit="m/s^2")


__all__ = [
    "NormalizedValue",
    "UnitConversionError",
    "length_to_m",
    "speed_to_mps",
    "force_to_newtons",
    "angle_to_deg",
    "time_to_seconds",
    "acceleration_to_mps2",
]
