"""Language pipeline that ends with MuJoCo Panda execution."""

from __future__ import annotations

from pathlib import Path

from lang2mech_ir.pipeline import LanguageToActionPipeline
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

INSTRUCTIONS = [
    "Slowly insert the 10 mm peg that is 100 mm long into the hole carefully, without using more than 5 N of force.",
    "Quickly insert the 12 mm peg with 30 N limit into the chamfered hole, keep alignment below 1 degree.",
]


def main() -> None:
    model_path = Path("mujoco_menagerie-main/franka_emika_panda/scene.xml").resolve()
    if not model_path.exists():
        raise SystemExit(
            "scene.xml missing. Download google-deepmind/mujoco_menagerie and place franka_emika_panda/ under mujoco_menagerie-main/."
        )

    joint_names = [f"joint{i}" for i in range(1, 8)]
    actuator_names = [f"actuator{i}" for i in range(1, 8)]

    pipeline = LanguageToActionPipeline()
    for instruction in INSTRUCTIONS:
        result = pipeline.process_instruction(instruction)
        goal_positions = [0.0] * len(joint_names)
        goal_positions[-1] = result.ir.hole.depth_m
        log = run_mujoco_episode(
            result.ir,
            model_path,
            steps=200,
            joint_names=joint_names,
            actuator_names=actuator_names,
            goal_positions=goal_positions,
        )
        final_depth = log.positions_m[-1]
        final_force = log.contact_forces_N[-1]
        print(
            f"Instruction: {instruction[:70]}...\n"
            f"  success={result.metrics.success} (1D) final_depth_1d={result.metrics.final_depth_m:.3f} m\n"
            f"  MuJoCo Panda final_depth={final_depth:.3f} m final_force={final_force:.2f} N\n"
        )


if __name__ == "__main__":  # pragma: no cover - manual script
    main()
