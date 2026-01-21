"""Batch-run language instructions and record Panda MuJoCo results."""

from __future__ import annotations

import json
from pathlib import Path

from lang2mech_ir.pipeline import LanguageToActionPipeline
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

INSTRUCTIONS = [
    "Slowly insert the 10 mm peg that is 100 mm long into the hole carefully, without using more than 5 N of force.",
    "Perform a spiral search to insert the 8 mm peg into the 8.3 mm sleeve, keep forces under 15 N and finish within 6 seconds.",
    "Quickly insert the 12 mm peg with 30 N limit into the chamfered hole, keep alignment below 1 degree.",
    "Insert the lubricated 9 mm peg into the 9.2 mm hole within 4 seconds, max force 12 N.",
]


def main() -> None:
    model_path = Path("mujoco_menagerie-main/franka_emika_panda/scene.xml").resolve()
    if not model_path.exists():
        raise SystemExit("Expected MuJoCo menagerie assets under mujoco_menagerie-main/")

    joint_names = [f"joint{i}" for i in range(1, 8)]
    actuator_names = [f"actuator{i}" for i in range(1, 8)]

    pipeline = LanguageToActionPipeline()
    results = []
    for instruction in INSTRUCTIONS:
        res = pipeline.process_instruction(instruction)
        goal_positions = [0.0] * len(joint_names)
        goal_positions[-1] = res.ir.hole.depth_m
        panda_log = run_mujoco_episode(
            res.ir,
            model_path,
            steps=250,
            joint_names=joint_names,
            actuator_names=actuator_names,
            goal_positions=goal_positions,
        )
        results.append(
            {
                "instruction": instruction,
                "ir": res.ir.to_dict(),
                "metrics_1d": res.metrics.as_dict(),
                "panda_final_depth_m": panda_log.positions_m[-1],
                "panda_final_force_N": panda_log.contact_forces_N[-1],
                "panda_steps": len(panda_log.times_s),
            }
        )
        print(
            f"Instruction: {instruction[:80]}...\n"
            f"  1D success={res.metrics.success} depth={res.metrics.final_depth_m:.3f} force={res.metrics.final_force_N:.2f}\n"
            f"  Panda depth={panda_log.positions_m[-1]:.3f} force={panda_log.contact_forces_N[-1]:.2f} steps={len(panda_log.times_s)}\n"
        )

    out_path = Path("results/panda_pipeline.json")
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved {len(results)} Panda runs to {out_path}.")


if __name__ == "__main__":
    main()
