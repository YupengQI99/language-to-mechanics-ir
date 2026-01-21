"""Data structures representing the Mechanics IR."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import copy


@dataclass
class ConstraintBounds:
    """Describes scalar bounds for a constraint quantity (e.g., force)."""

    minimum: Optional[float] = None
    maximum: Optional[float] = None
    units: str = ""

    def clamp(self, value: float) -> float:
        """Clamp *value* within the bounds if they exist."""

        if self.minimum is not None and value < self.minimum:
            value = self.minimum
        if self.maximum is not None and value > self.maximum:
            value = self.maximum
        return value


@dataclass
class PegGeometry:
    radius_m: float = 0.005  # 5 mm
    length_m: float = 0.10
    chamfer_angle_deg: float = 3.0


@dataclass
class HoleGeometry:
    radius_m: float = 0.0055  # default 0.5 mm clearance
    depth_m: float = 0.05
    chamfer_angle_deg: float = 3.0


@dataclass
class MaterialProperties:
    friction_coefficient: float = 0.3
    peg_material: str = "generic"
    hole_material: str = "generic"
    lubrication: bool = False


@dataclass
class TrajectoryProfile:
    approach_speed_mps: float = 0.02
    insertion_speed_mps: float = 0.01
    retraction_speed_mps: float = 0.015
    approach_angle_deg: float = 0.0
    strategy: str = "straight_in"


@dataclass
class ToleranceSpecification:
    alignment_deg: float = 2.0
    position_m: float = 0.0005
    clearance_m: Optional[float] = None


@dataclass
class EnvironmentSettings:
    gravity_mps2: float = 9.81
    temperature_c: float = 22.0


@dataclass
class MechanicsIR:
    """Structured representation of peg-in-hole instructions."""

    task_name: str = "peg_in_hole"
    action_type: str = "peg_in_hole_insertion"
    peg: PegGeometry = field(default_factory=PegGeometry)
    hole: HoleGeometry = field(default_factory=HoleGeometry)
    materials: MaterialProperties = field(default_factory=MaterialProperties)
    tolerances: ToleranceSpecification = field(default_factory=ToleranceSpecification)
    trajectory: TrajectoryProfile = field(default_factory=TrajectoryProfile)
    max_force: ConstraintBounds = field(default_factory=lambda: ConstraintBounds(maximum=20.0, units="N"))
    time_limit_s: Optional[float] = None
    environment: EnvironmentSettings = field(default_factory=EnvironmentSettings)
    metadata: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return the IR as a deeply nested dictionary."""

        return asdict(self)

    def copy(self) -> "MechanicsIR":
        """Return a deep copy of the IR."""

        return copy.deepcopy(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "MechanicsIR":
        """Construct an IR from a dictionary (inverse of :meth:`to_dict`)."""

        default = cls()
        default_dict = default.to_dict()
        merged = _deep_merge(default_dict, payload)
        return cls(**{
            "task_name": merged["task_name"],
            "action_type": merged["action_type"],
            "peg": PegGeometry(**merged["peg"]),
            "hole": HoleGeometry(**merged["hole"]),
            "materials": MaterialProperties(**merged["materials"]),
            "tolerances": ToleranceSpecification(**merged["tolerances"]),
            "trajectory": TrajectoryProfile(**merged["trajectory"]),
            "max_force": ConstraintBounds(**merged["max_force"]),
            "time_limit_s": merged.get("time_limit_s"),
            "environment": EnvironmentSettings(**merged["environment"]),
            "metadata": merged.get("metadata", {}),
            "notes": merged.get("notes", []),
        })


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge helper for :meth:`MechanicsIR.from_dict`."""

    result: Dict[str, Any] = copy.deepcopy(base)
    for key, value in overrides.items():
        if key not in result:
            result[key] = value
            continue
        if isinstance(value, dict) and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "ConstraintBounds",
    "PegGeometry",
    "HoleGeometry",
    "MaterialProperties",
    "TrajectoryProfile",
    "ToleranceSpecification",
    "EnvironmentSettings",
    "MechanicsIR",
]
