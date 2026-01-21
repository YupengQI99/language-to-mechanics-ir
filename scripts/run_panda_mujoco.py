"""Run the Peg-In-Hole MPC on the Franka Panda MuJoCo model."""

from __future__ import annotations

from pathlib import Path

from lang2mech_ir import MechanicsIR
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode


def main() -> None:
    model_path = Path("mujoco_menagerie-main/franka_emika_panda/scene.xml").resolve()
    if not model_path.exists():
        raise SystemExit(
            "scene.xml not found. Please download google-deepmind/mujoco_menagerie "
            "and place franka_emika_panda/ under mujoco_menagerie-main/."
        )

    ir = MechanicsIR()
    ir.hole.depth_m = 0.05
    ir.max_force.maximum = 15.0

    joint_names = [f"joint{i}" for i in range(1, 8)]
    actuator_names = [f"actuator{i}" for i in range(1, 8)]
    goal_positions = [0.0] * len(joint_names)
    goal_positions[-1] = ir.hole.depth_m

    log = run_mujoco_episode(
        ir,
        model_path,
        steps=300,
        joint_names=joint_names,
        actuator_names=actuator_names,
        goal_positions=goal_positions,
    )

    print(f"Episode steps: {len(log.times_s)} final depth: {log.positions_m[-1]:.4f} m")
    print(f"Final force: {log.contact_forces_N[-1]:.2f} N")


if __name__ == "__main__":  # pragma: no cover - manual script
    main()
