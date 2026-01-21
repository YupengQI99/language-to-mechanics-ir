"""Instruction parser that maps structured LLM output to the Mechanics IR."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable

from . import units
from .ir_schema import MechanicsIR


class InstructionParser:
    """Transforms structured instruction dictionaries into a :class:`MechanicsIR`."""

    def __init__(self, base_ir: MechanicsIR | None = None) -> None:
        self.base_ir = base_ir or MechanicsIR()

    def parse(self, instruction: Mapping[str, Any]) -> MechanicsIR:
        """Return a :class:`MechanicsIR` by normalizing *instruction* values."""

        if not isinstance(instruction, Mapping):
            raise TypeError("Instruction payload must be a mapping.")

        ir = self.base_ir.copy()
        notes: list[str] = []

        self._apply_task_fields(instruction, ir)
        self._apply_peg_fields(instruction, ir, notes)
        self._apply_hole_fields(instruction, ir, notes)
        self._apply_material_fields(instruction, ir)
        self._apply_trajectory_fields(instruction, ir, notes)
        self._apply_tolerance_fields(instruction, ir, notes)
        self._apply_force_fields(instruction, ir, notes)
        self._apply_time_limit(instruction, ir, notes)
        self._apply_environment_fields(instruction, ir, notes)

        if notes:
            ir.notes.extend(notes)
        return ir

    # ------------------------------------------------------------------ helpers
    def _apply_task_fields(self, payload: Mapping[str, Any], ir: MechanicsIR) -> None:
        action_type = self._first_value(payload, ("action_type", "action", "task"))
        if action_type:
            ir.action_type = str(action_type)
        task_name = self._first_value(payload, ("task_name", "task"))
        if task_name:
            ir.task_name = str(task_name)

    def _apply_peg_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("peg", "peg_dimensions", "peg_geometry"))
        if section is None:
            section = {}
        radius_value = self._first_value(section, ("radius", "radius_m", "radius_mm"))
        diameter_value = self._first_value(section, ("diameter", "diameter_m"))
        if radius_value is None:
            radius_value = self._first_value(payload, ("peg_radius",))
        if radius_value is None and diameter_value is not None:
            normalized_diameter = self._normalize(units.length_to_m, diameter_value, "peg.diameter", notes)
            ir.peg.radius_m = normalized_diameter.value / 2.0
        elif radius_value is not None:
            normalized_radius = self._normalize(units.length_to_m, radius_value, "peg.radius", notes)
            ir.peg.radius_m = normalized_radius.value
        length_value = self._first_value(section, ("length", "length_m")) or self._first_value(payload, ("peg_length",))
        if length_value is not None:
            normalized_length = self._normalize(units.length_to_m, length_value, "peg.length", notes)
            ir.peg.length_m = normalized_length.value
        chamfer_value = self._first_value(section, ("chamfer_angle", "chamfer_angle_deg"))
        if chamfer_value is not None:
            chamfer = self._normalize(units.angle_to_deg, chamfer_value, "peg.chamfer_angle", notes)
            ir.peg.chamfer_angle_deg = chamfer.value

    def _apply_hole_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("hole", "hole_dimensions"))
        if section is None:
            section = {}
        radius_value = self._first_value(section, ("radius", "radius_m"))
        diameter_value = self._first_value(section, ("diameter", "diameter_m"))
        if radius_value is None:
            radius_value = self._first_value(payload, ("hole_radius",))
        if radius_value is None and diameter_value is not None:
            normalized_diameter = self._normalize(units.length_to_m, diameter_value, "hole.diameter", notes)
            ir.hole.radius_m = normalized_diameter.value / 2.0
        elif radius_value is not None:
            normalized_radius = self._normalize(units.length_to_m, radius_value, "hole.radius", notes)
            ir.hole.radius_m = normalized_radius.value
        depth_value = self._first_value(section, ("depth", "depth_m")) or self._first_value(payload, ("hole_depth",))
        if depth_value is not None:
            normalized_depth = self._normalize(units.length_to_m, depth_value, "hole.depth", notes)
            ir.hole.depth_m = normalized_depth.value
        chamfer_value = self._first_value(section, ("chamfer_angle", "chamfer_angle_deg"))
        if chamfer_value is not None:
            chamfer = self._normalize(units.angle_to_deg, chamfer_value, "hole.chamfer_angle", notes)
            ir.hole.chamfer_angle_deg = chamfer.value

    def _apply_material_fields(self, payload: Mapping[str, Any], ir: MechanicsIR) -> None:
        section = self._mapping_for(payload, ("material_properties", "materials"))
        if section is None:
            return
        friction = self._first_value(section, ("friction", "friction_coefficient"))
        if friction is not None:
            ir.materials.friction_coefficient = float(friction)
        peg_mat = section.get("peg_material")
        if peg_mat:
            ir.materials.peg_material = str(peg_mat)
        hole_mat = section.get("hole_material")
        if hole_mat:
            ir.materials.hole_material = str(hole_mat)
        if "lubrication" in section:
            ir.materials.lubrication = bool(section["lubrication"])

    def _apply_trajectory_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("trajectory", "trajectory_profile", "motion_profile")) or {}
        insertion_speed = (
            self._first_value(section, ("insertion_speed", "speed"))
            or payload.get("speed")
            or payload.get("insertion_speed")
        )
        if insertion_speed is not None:
            normalized_speed = self._normalize(units.speed_to_mps, insertion_speed, "trajectory.insertion_speed", notes)
            ir.trajectory.insertion_speed_mps = normalized_speed.value
        approach_speed = self._first_value(section, ("approach_speed",))
        if approach_speed is not None:
            normalized = self._normalize(units.speed_to_mps, approach_speed, "trajectory.approach_speed", notes)
            ir.trajectory.approach_speed_mps = normalized.value
        retraction_speed = self._first_value(section, ("retraction_speed",))
        if retraction_speed is not None:
            normalized = self._normalize(units.speed_to_mps, retraction_speed, "trajectory.retraction_speed", notes)
            ir.trajectory.retraction_speed_mps = normalized.value
        strategy = self._first_value(section, ("strategy", "trajectory_strategy")) or payload.get("trajectory_strategy")
        if strategy:
            ir.trajectory.strategy = str(strategy)
        approach_angle = self._first_value(section, ("approach_angle", "approach_angle_deg")) or payload.get(
            "approach_angle"
        )
        if approach_angle is not None:
            normalized = self._normalize(units.angle_to_deg, approach_angle, "trajectory.approach_angle", notes)
            ir.trajectory.approach_angle_deg = normalized.value

    def _apply_tolerance_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("tolerances",)) or {}
        alignment = (
            self._first_value(section, ("alignment", "alignment_tolerance"))
            or payload.get("alignment_tolerance")
        )
        if alignment is not None:
            normalized = self._normalize(units.angle_to_deg, alignment, "tolerances.alignment", notes)
            ir.tolerances.alignment_deg = normalized.value
        position = (
            self._first_value(section, ("position", "position_tolerance"))
            or payload.get("position_tolerance")
        )
        if position is not None:
            normalized = self._normalize(units.length_to_m, position, "tolerances.position", notes)
            ir.tolerances.position_m = normalized.value
        clearance = (
            self._first_value(section, ("clearance", "clearance_m"))
            or payload.get("clearance")
        )
        if clearance is not None:
            normalized = self._normalize(units.length_to_m, clearance, "tolerances.clearance", notes)
            ir.tolerances.clearance_m = normalized.value

    def _apply_force_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("max_force", "force_limit", "force_limits"))
        if section is not None and isinstance(section, Mapping):
            maximum = self._first_value(section, ("maximum", "max"))
            minimum = self._first_value(section, ("minimum", "min"))
            if maximum is not None:
                normalized = self._normalize(units.force_to_newtons, maximum, "force.maximum", notes)
                ir.max_force.maximum = normalized.value
            if minimum is not None:
                normalized = self._normalize(units.force_to_newtons, minimum, "force.minimum", notes)
                ir.max_force.minimum = normalized.value
            if "units" in section:
                ir.max_force.units = str(section["units"])
        else:
            max_force_value = self._first_value(payload, ("max_force", "force_limit", "force"))
            if max_force_value is not None:
                normalized = self._normalize(units.force_to_newtons, max_force_value, "force.maximum", notes)
                ir.max_force.maximum = normalized.value
        if not ir.max_force.units:
            ir.max_force.units = "N"

    def _apply_time_limit(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        time_value = self._first_value(payload, ("time_limit", "duration", "deadline"))
        if time_value is None:
            return
        normalized = self._normalize(units.time_to_seconds, time_value, "time_limit", notes)
        ir.time_limit_s = normalized.value

    def _apply_environment_fields(self, payload: Mapping[str, Any], ir: MechanicsIR, notes: list[str]) -> None:
        section = self._mapping_for(payload, ("environment", "env"))
        if section is None:
            return
        gravity = section.get("gravity")
        if gravity is not None:
            normalized = self._normalize(units.acceleration_to_mps2, gravity, "environment.gravity", notes)
            ir.environment.gravity_mps2 = normalized.value
        temperature = section.get("temperature")
        if temperature is not None:
            ir.environment.temperature_c = float(temperature)

    # ------------------------------------------------------------------ utilities
    @staticmethod
    def _note_if_assumed(notes: list[str], field: str, normalized: units.NormalizedValue) -> None:
        if normalized.assumed_unit:
            notes.append(f"Assumed {normalized.unit} for {field} (input={normalized.source!r}).")

    def _normalize(
        self,
        converter,
        value: Any,
        field: str,
        notes: list[str],
        **kwargs: Any,
    ) -> units.NormalizedValue:
        try:
            normalized = converter(value, **kwargs)
        except units.UnitConversionError as exc:  # pragma: no cover - wrapped for clarity
            raise ValueError(f"{field}: {exc}") from exc
        self._note_if_assumed(notes, field, normalized)
        return normalized

    @staticmethod
    def _first_value(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    @staticmethod
    def _mapping_for(payload: Mapping[str, Any], keys: Iterable[str]) -> Mapping[str, Any] | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, Mapping):
                return value
        return None
