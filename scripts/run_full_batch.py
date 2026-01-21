"""Generate a larger instruction set and run both 1D + MuJoCo Panda experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from lang2mech_ir.pipeline import LanguageToActionPipeline
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

PEG_RADII_MM = [8, 9, 10, 11, 12]
HOLE_CLEARANCES_MM = [0.2, 0.4]
FORCE_LIMITS_N = [5, 10, 15, 20, 25]
SPEED_DESCRIPTORS = ["carefully", "steadily"]  # 5*2*5*2 = 100


def build_instruction(radius_mm: float, clearance_mm: float, force: float, speed_word: str) -> str:
    hole_radius_mm = radius_mm + clearance_mm
    return (
        f"{speed_word.capitalize()} insert the {radius_mm:.0f} mm peg into the {hole_radius_mm:.1f} mm hole, "
        f"keep forces under {force} N and ensure alignment below 1 degree."
    )


def generate_instructions() -> List[str]:
    instructions: List[str] = []
    for radius in PEG_RADII_MM:
        for clearance in HOLE_CLEARANCES_MM:
            for force in FORCE_LIMITS_N:
                for speed in SPEED_DESCRIPTORS:
                    instructions.append(build_instruction(radius, clearance, force, speed))
    return instructions


def main() -> None:
    instructions = generate_instructions()[:50]
    print(f"Running {len(instructions)} instructions.")

    model_path = Path("mujoco_menagerie-main/franka_emika_panda/scene.xml").resolve()
    if not model_path.exists():
        raise SystemExit("MuJoCo menagerie Panda assets missing.")

    joint_names = [f"joint{i}" for i in range(1, 8)]
    actuator_names = [f"actuator{i}" for i in range(1, 8)]

    pipeline = LanguageToActionPipeline()
    all_results = []
    for idx, instruction in enumerate(instructions, 1):
        result = pipeline.process_instruction(instruction)
        goal_positions = [0.0] * len(joint_names)
        goal_positions[-1] = result.ir.hole.depth_m
        panda_log = run_mujoco_episode(
            result.ir,
            model_path,
            steps=100,
            joint_names=joint_names,
            actuator_names=actuator_names,
            goal_positions=goal_positions,
        )
        all_results.append(
            {
                "instruction": instruction,
                "ir": result.ir.to_dict(),
                "metrics_1d": result.metrics.as_dict(),
                "panda_final_depth_m": panda_log.positions_m[-1],
                "panda_final_force_N": panda_log.contact_forces_N[-1],
                "panda_steps": len(panda_log.times_s),
            }
        )
        if idx % 5 == 0:
            print(f"Processed {idx}/{len(instructions)} instructions...")

    output_path = Path("results/panda_full_batch.json")
    output_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
