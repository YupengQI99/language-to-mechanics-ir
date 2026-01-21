"""Mechanics Auditor implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .ir_schema import MechanicsIR


@dataclass
class AuditResult:
    """Outcome of auditing a MechanicsIR instance."""

    valid: bool
    observations: List[str] = field(default_factory=list)
    corrected_ir: MechanicsIR = field(default_factory=MechanicsIR)


class MechanicsAuditor:
    """Rule-based checker that enforces geometric and dynamic feasibility."""

    def __init__(
        self,
        *,
        min_clearance_m: float = 1e-4,
        conservative_speed_mps: float = 0.01,
        max_speed_mps: float = 0.05,
        low_force_threshold_n: float = 8.0,
        max_alignment_deg: float = 5.0,
    ) -> None:
        self.min_clearance_m = min_clearance_m
        self.conservative_speed_mps = conservative_speed_mps
        self.max_speed_mps = max_speed_mps
        self.low_force_threshold_n = low_force_threshold_n
        self.max_alignment_deg = max_alignment_deg

    def audit(self, ir: MechanicsIR) -> AuditResult:
        corrected = ir.copy()
        notes: List[str] = []
        self._ensure_positive_dimensions(corrected, notes)
        clearance_ok = self._enforce_clearance(corrected, notes)
        self._enforce_length_depth_relation(corrected, notes)
        self._enforce_tolerances(corrected, notes)
        self._enforce_force_limits(corrected, notes)
        self._enforce_speed_limits(corrected, notes)
        self._check_material_properties(corrected, notes)
        self._check_environment(corrected, notes)

        if not notes:
            notes.append("IR passed auditor checks without modification.")

        return AuditResult(valid=clearance_ok, observations=notes, corrected_ir=corrected)

    # ------------------------------------------------------------------ helpers
    def _ensure_positive_dimensions(self, ir: MechanicsIR, notes: List[str]) -> None:
        if ir.peg.radius_m <= 0:
            ir.peg.radius_m = 0.001
            notes.append("Peg radius missing or non-positive; defaulted to 1 mm.")
        if ir.peg.length_m <= 0:
            ir.peg.length_m = 0.05
            notes.append("Peg length missing or non-positive; defaulted to 5 cm.")
        if ir.hole.radius_m <= 0:
            ir.hole.radius_m = ir.peg.radius_m + self.min_clearance_m
            notes.append("Hole radius invalid; expanded to maintain clearance.")
        if ir.hole.depth_m <= 0:
            ir.hole.depth_m = min(ir.peg.length_m * 0.5, 0.05)
            notes.append("Hole depth invalid; set to a conservative value.")

    def _enforce_clearance(self, ir: MechanicsIR, notes: List[str]) -> bool:
        clearance = ir.hole.radius_m - ir.peg.radius_m
        if clearance < self.min_clearance_m:
            adjustment = self.min_clearance_m - clearance
            ir.hole.radius_m += adjustment
            clearance = self.min_clearance_m
            notes.append(
                f"Increased hole radius by {adjustment:.6f} m to ensure minimum clearance."
            )
        if ir.tolerances.clearance_m is None or ir.tolerances.clearance_m > clearance:
            ir.tolerances.clearance_m = clearance
            notes.append("Updated clearance tolerance to match achievable geometry.")
        return clearance >= self.min_clearance_m

    def _enforce_length_depth_relation(self, ir: MechanicsIR, notes: List[str]) -> None:
        if ir.hole.depth_m > ir.peg.length_m:
            notes.append(
                "Hole depth exceeds peg length; insertion may not fully seat the peg."
            )

    def _enforce_tolerances(self, ir: MechanicsIR, notes: List[str]) -> None:
        if ir.tolerances.alignment_deg <= 0:
            ir.tolerances.alignment_deg = 1.0
            notes.append("Alignment tolerance non-positive; reset to 1 degree.")
        if ir.tolerances.alignment_deg > self.max_alignment_deg:
            ir.tolerances.alignment_deg = self.max_alignment_deg
            notes.append(
                f"Alignment tolerance tightened to {self.max_alignment_deg} degrees for accuracy."
            )
        if ir.tolerances.position_m <= 0:
            ir.tolerances.position_m = 5e-4
            notes.append("Position tolerance non-positive; reset to 0.5 mm.")

    def _enforce_force_limits(self, ir: MechanicsIR, notes: List[str]) -> None:
        max_force = ir.max_force.maximum
        if max_force is None or max_force <= 0:
            ir.max_force.maximum = 10.0
            ir.max_force.units = "N"
            notes.append("Max force unspecified; defaulted to 10 N.")
        if ir.max_force.minimum is not None and ir.max_force.minimum < 0:
            ir.max_force.minimum = 0.0
            notes.append("Negative minimum force replaced with 0 N.")
        if (
            ir.max_force.minimum is not None
            and ir.max_force.maximum is not None
            and ir.max_force.minimum > ir.max_force.maximum
        ):
            ir.max_force.minimum = None
            notes.append("Minimum force exceeded maximum; cleared minimum constraint.")

    def _enforce_speed_limits(self, ir: MechanicsIR, notes: List[str]) -> None:
        def clamp_speed(value: float) -> float:
            if value <= 0:
                return self.conservative_speed_mps
            return min(value, self.max_speed_mps)

        original_speed = ir.trajectory.insertion_speed_mps
        ir.trajectory.insertion_speed_mps = clamp_speed(ir.trajectory.insertion_speed_mps)
        if ir.trajectory.insertion_speed_mps != original_speed:
            notes.append(
                f"Insertion speed clamped to {ir.trajectory.insertion_speed_mps:.3f} m/s for safety."
            )
        if (
            ir.max_force.maximum is not None
            and ir.max_force.maximum < self.low_force_threshold_n
            and ir.trajectory.insertion_speed_mps > self.conservative_speed_mps
        ):
            ir.trajectory.insertion_speed_mps = self.conservative_speed_mps
            notes.append(
                "Reduced insertion speed to maintain low-force requirement."
            )
        ir.trajectory.approach_speed_mps = clamp_speed(ir.trajectory.approach_speed_mps)
        ir.trajectory.retraction_speed_mps = clamp_speed(ir.trajectory.retraction_speed_mps)

    def _check_material_properties(self, ir: MechanicsIR, notes: List[str]) -> None:
        friction = ir.materials.friction_coefficient
        if friction <= 0 or friction > 1.0:
            ir.materials.friction_coefficient = 0.3
            notes.append("Friction coefficient out of range; reset to 0.3.")

    def _check_environment(self, ir: MechanicsIR, notes: List[str]) -> None:
        if ir.environment.gravity_mps2 <= 0:
            ir.environment.gravity_mps2 = 9.81
            notes.append("Gravity invalid; reset to 9.81 m/s^2.")
