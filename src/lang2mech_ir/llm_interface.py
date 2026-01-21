"""LLM interface with heuristic and API-backed compilation paths."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Tuple

from .ir_schema import MechanicsIR
from .parser import InstructionParser


logger = logging.getLogger(__name__)


class LLMInterface:
    """Translate instructions into Mechanics IR using heuristics or Claude API."""

    _MEASURE_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z0-9°/\^]+)", re.IGNORECASE)

    _PEG_WORDS = ("peg", "pin", "shaft", "rod")
    _HOLE_WORDS = ("hole", "socket", "bushing", "slot")
    _CLEARANCE_WORDS = ("clearance", "gap", "play")
    _FORCE_WORDS = ("force", "load", "push", "pressure")
    _SPEED_WORDS = ("speed", "velocity", "feed", "rate", "insert", "drive")
    _TOLERANCE_WORDS = ("tolerance", "align", "alignment", "accuracy", "precision")
    _DEPTH_WORDS = ("depth", "deep")
    _LENGTH_WORDS = ("length", "long", "lengthwise")
    _RETRACT_WORDS = ("retract", "withdraw", "pull")
    _APPROACH_WORDS = ("approach", "advance")

    _REMOTE_SYSTEM_PROMPT = (
        "You are an interface for a peg-in-hole robotics controller. "
        "Return strictly valid JSON that follows the schema and uses numeric SI values."
    )
    _REMOTE_SCHEMA = """{
  "action_type": "peg_in_hole_insertion",
  "task_name": "peg_in_hole",
  "peg_dimensions": {"radius": "0.005 m", "diameter": "0.01 m", "length": "0.05 m"},
  "hole_dimensions": {"radius": "0.0052 m", "diameter": "0.0104 m", "depth": "0.04 m"},
  "material_properties": {"friction_coefficient": 0.3, "lubrication": true},
  "trajectory": {
    "approach_speed": "0.02 m/s",
    "insertion_speed": "0.01 m/s",
    "retraction_speed": "0.02 m/s",
    "strategy": "straight_in",
    "approach_angle": "0 deg"
  },
  "alignment_tolerance": "2 deg",
  "position_tolerance": "0.0005 m",
  "clearance": "0.0002 m",
  "max_force": {"maximum": "15 N", "minimum": "0 N"},
  "time_limit": "10 s",
  "environment": {"gravity": "9.81 m/s^2", "temperature": 22}
}"""

    def __init__(
        self,
        parser: InstructionParser | None = None,
        *,
        use_remote: bool = False,
        model: str = "claude-3-5-sonnet-20240620",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        self.parser = parser or InstructionParser()
        self.use_remote = use_remote
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    # ------------------------------------------------------------------ public API
    def interpret(self, instruction: str) -> Dict[str, Any]:
        """Return a structured dictionary derived from *instruction*."""

        if self.use_remote:
            remote = self._interpret_with_remote(instruction)
            if remote is not None:
                return remote
        return self._interpret_locally(instruction)

    def _interpret_locally(self, instruction: str) -> Dict[str, Any]:
        """Heuristic fallback used when no remote LLM is configured."""

        structured: Dict[str, Any] = {
            "action_type": "peg_in_hole_insertion",
            "task_name": "peg_in_hole",
            "peg_dimensions": {},
            "hole_dimensions": {},
            "material_properties": {},
            "trajectory": {},
            "max_force": {},
            "environment": {},
        }
        lower_text = instruction.lower()
        self._apply_keyword_heuristics(lower_text, structured)
        for measurement in self._extract_measurements(instruction):
            self._assign_measurement(lower_text, structured, measurement)
        self._cleanup(structured)
        return structured

    # ------------------------------------------------------------------ remote LLM
    def _interpret_with_remote(self, instruction: str) -> Dict[str, Any] | None:
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY is not set; falling back to heuristic parser.")
            return None
        try:
            return self._call_remote_claude(instruction)
        except Exception as exc:  # pragma: no cover - depends on network/API
            logger.warning("Claude call failed (%s); reverting to heuristics.", exc)
            return None

    def _call_remote_claude(self, instruction: str) -> Dict[str, Any]:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - no runtime dependency for tests
            raise RuntimeError(
                "anthropic package is required for remote LLM integration."
            ) from exc

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)

        prompt = self._build_remote_prompt(instruction)
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self._REMOTE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text_content = self._extract_text_from_response(response)
        if not text_content:
            raise RuntimeError("Claude returned no text content.")
        return self._parse_remote_json(text_content)

    def _build_remote_prompt(self, instruction: str) -> str:
        return (
            "Convert the following instruction into JSON for the Mechanics IR schema. "
            "All numeric values must be explicit numbers with SI units (e.g., 0.01 m/s). "
            "Never respond with qualitative adjectives like 'slow'; always give numeric quantities. "
            "Include only the fields you can infer.\n\n"
            f"Instruction:\n{instruction}\n\n"
            "Respond with JSON only. Example schema:\n"
            f"{self._REMOTE_SCHEMA}\n"
        )

    @staticmethod
    def _extract_text_from_response(response: Any) -> str:
        content_blocks = getattr(response, "content", [])
        chunks: List[str] = []
        for block in content_blocks:
            block_type = getattr(block, "type", None)
            text = getattr(block, "text", None)
            if block_type == "text" and isinstance(text, str):
                chunks.append(text)
        return "\n".join(chunks).strip()

    @staticmethod
    def _parse_remote_json(payload: str) -> Dict[str, Any]:
        candidate = payload.strip()
        if candidate.startswith("```"):
            parts = candidate.split("```", 2)
            if len(parts) >= 2:
                candidate = parts[1].strip()
        if not candidate.startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("Claude response did not contain JSON")
            candidate = candidate[start : end + 1]
        return json.loads(candidate)

    def compile(self, instruction: str) -> MechanicsIR:
        """Return a finalized :class:`MechanicsIR` from *instruction*."""

        structured = self.interpret(instruction)
        return self.parser.parse(structured)

    # ------------------------------------------------------------------ heuristics
    def _apply_keyword_heuristics(self, lower_text: str, data: Dict[str, Any]) -> None:
        def contains(words: Iterable[str]) -> bool:
            return any(word in lower_text for word in words)

        if contains(("slow", "slowly", "gentle", "gently")):
            self._assign_once(data, "trajectory.insertion_speed", "0.002 m/s")
            self._assign_once(data, "max_force.maximum", "5 N")
        if contains(("fast", "quick", "rapid")):
            self._assign_once(data, "trajectory.insertion_speed", "0.05 m/s")
        if "spiral" in lower_text:
            self._assign_once(data, "trajectory.strategy", "spiral_search")
        elif "straight" in lower_text:
            self._assign_once(data, "trajectory.strategy", "straight_in")
        if contains(("careful", "carefully", "precise", "precision", "accurate")):
            self._assign_once(data, "alignment_tolerance", "1 deg")
            self._assign_once(data, "position_tolerance", "0.0003 m")
        if contains(("tight fit", "press-fit", "press fit")):
            self._assign_once(data, "clearance", "0.0001 m")
        elif "loose" in lower_text:
            self._assign_once(data, "clearance", "0.0005 m")
        if contains(("lubricated", "lubrication", "oiled")):
            self._assign_once(data, "materials.lubrication", True)
        if contains(("dry",)):
            self._assign_once(data, "materials.lubrication", False)

    # ------------------------------------------------------------------ measurement extraction
    def _extract_measurements(self, instruction: str) -> List[Tuple[str, str, Tuple[int, int]]]:
        matches: List[Tuple[str, str, Tuple[int, int]]] = []
        for match in self._MEASURE_PATTERN.finditer(instruction):
            value = match.group("value")
            unit = match.group("unit")
            canonical_unit = self._canonical_unit(unit)
            if canonical_unit is None:
                continue
            measurement = f"{value} {canonical_unit}"
            matches.append((measurement, canonical_unit, match.span()))
        return matches

    def _assign_measurement(
        self,
        lower_text: str,
        data: Dict[str, Any],
        measurement: Tuple[str, str, Tuple[int, int]],
    ) -> None:
        value_with_unit, canonical_unit, span = measurement
        pre_context = lower_text[max(0, span[0] - 40) : span[0]]
        post_context = lower_text[span[1] : min(len(lower_text), span[1] + 40)]
        context = pre_context + post_context
        near_pre = lower_text[max(0, span[0] - 16) : span[0]]
        near_post = lower_text[span[1] : min(len(lower_text), span[1] + 16)]
        near_context = near_pre + near_post
        length_marker = self._contains_any(near_context, self._LENGTH_WORDS)
        depth_marker = self._contains_any(near_context, self._DEPTH_WORDS)
        peg_score = self._context_score(context, near_context, self._PEG_WORDS)
        hole_score = self._context_score(context, near_context, self._HOLE_WORDS)

        if canonical_unit in {"mm", "cm", "m", "um"}:
            if depth_marker and hole_score > 0:
                self._assign_once(data, "hole.depth", value_with_unit)
                return
            if self._contains_any(context, self._CLEARANCE_WORDS):
                self._assign_once(data, "clearance", value_with_unit)
                return
            if self._contains_any(context, ("position", "offset")) or self._contains_any(context, self._TOLERANCE_WORDS):
                self._assign_once(data, "position_tolerance", value_with_unit)
                return
            if peg_score > hole_score and length_marker:
                self._assign_once(data, "peg.length", value_with_unit)
                return
            if peg_score >= hole_score and peg_score > 0:
                if "radius" in context:
                    self._assign_once(data, "peg.radius", value_with_unit)
                else:
                    self._assign_once(data, "peg.diameter", value_with_unit)
                return
            if hole_score > 0:
                if "radius" in context:
                    self._assign_once(data, "hole.radius", value_with_unit)
                else:
                    self._assign_once(data, "hole.diameter", value_with_unit)
                return
        elif canonical_unit in {"mm/s", "cm/s", "m/s"}:
            if self._contains_any(near_pre, self._APPROACH_WORDS):
                self._assign_once(data, "trajectory.approach_speed", value_with_unit)
            elif self._contains_any(near_pre, self._RETRACT_WORDS):
                self._assign_once(data, "trajectory.retraction_speed", value_with_unit)
            else:
                self._assign_once(data, "trajectory.insertion_speed", value_with_unit)
            return
        elif canonical_unit in {"N", "kN"}:
            normalized = value_with_unit.replace("n", "N")
            self._assign_once(data, "max_force.maximum", normalized)
            return
        elif canonical_unit == "deg":
            if self._contains_any(context, self._TOLERANCE_WORDS):
                self._assign_once(data, "alignment_tolerance", value_with_unit)
            elif self._contains_any(context, self._APPROACH_WORDS):
                self._assign_once(data, "trajectory.approach_angle", value_with_unit)
            else:
                self._assign_once(data, "alignment_tolerance", value_with_unit)
            return
        elif canonical_unit in {"s", "ms", "min", "hr"}:
            self._assign_once(data, "time_limit", value_with_unit)
            return
        elif canonical_unit in {"m/s^2"}:
            if "gravity" in context:
                self._assign_once(data, "environment.gravity", value_with_unit)
            return

        if canonical_unit in {"s"} and self._contains_any(context, self._SPEED_WORDS):
            self._assign_once(data, "trajectory.insertion_speed", f"{value_with_unit} / step")

    # ------------------------------------------------------------------ utilities
    def _assign_once(self, data: Dict[str, Any], slot: str, value: Any) -> bool:
        if slot.startswith("peg."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("peg_dimensions", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot.startswith("hole."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("hole_dimensions", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot.startswith("trajectory."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("trajectory", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot.startswith("max_force."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("max_force", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot.startswith("materials."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("material_properties", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot.startswith("environment."):
            field = slot.split(".", 1)[1]
            bucket = data.setdefault("environment", {})
            if field not in bucket:
                bucket[field] = value
                return True
            return False
        if slot not in data:
            data[slot] = value
            return True
        return False

    def _cleanup(self, data: Dict[str, Any]) -> None:
        for key in ("peg_dimensions", "hole_dimensions", "material_properties", "trajectory", "max_force", "environment"):
            if key in data and not data[key]:
                del data[key]

    def _contains_any(self, text: str, patterns: Iterable[str]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _context_score(self, context: str, near_context: str, patterns: Iterable[str]) -> int:
        score = 0
        if self._contains_any(context, patterns):
            score += 1
        if self._contains_any(near_context, patterns):
            score += 2
        return score

    def _canonical_unit(self, unit: str) -> str | None:
        token = unit.strip().lower().replace("°", "deg")
        token = token.replace("per", "/").replace(" ", "")
        token = token.replace("seconds", "s").replace("second", "s")
        token = token.replace("millimeters", "mm").replace("millimeter", "mm")
        token = token.replace("centimeters", "cm").replace("centimeter", "cm")
        token = token.replace("meters", "m").replace("meter", "m")
        token = token.replace("newtons", "n").replace("newton", "n")
        token = token.replace("degrees", "deg").replace("degree", "deg")
        token = token.replace("minutes", "min").replace("minute", "min")
        token = token.replace("hours", "hr").replace("hour", "hr")
        if token in {"mm", "cm", "m", "um", "mm/s", "cm/s", "m/s", "deg", "s", "ms", "min", "hr", "m/s^2"}:
            return token
        if token == "n":
            return "N"
        if token == "kn":
            return "kN"
        if token == "g":
            return "m/s^2"
        return None
