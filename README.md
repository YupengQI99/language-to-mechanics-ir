# Language-to-Mechanics IR Compiler with Auditor

This repository implements the research plan for converting natural language peg-in-hole instructions into executable robot control constraints. The system is decomposed into explicit modules that mirror the plan:

- **LLM Interface & IR Compiler** – receives language instructions and emits a structured Mechanics IR.
- **Mechanics IR Format & Parser** – defines dataclasses plus unit normalization utilities for the IR.
- **Mechanics Auditor** – checks the IR for physical consistency and enforces safe defaults.
- **MPC Controller & Simulator** – simplified OSQP-based MPC plus a 1-D simulator emulate the execution stack before MuJoCo integration.
- **MuJoCo Interface (scaffold)** – `lang2mech_ir.simulation.mujoco_interface.MujocoPegInHoleEnv` provides a thin wrapper so the MPC can be plugged into a real MuJoCo scene once assets are available (including the multi-DoF Panda demo).
- **Metrics & Logging** – `logging_utils.metrics` computes success/force stats per episode for the evaluation section.
- **Data logging / Monitoring (future work)** – placeholder for telemetry capture once the controller exists.

## Repository layout

```
README.md                  — project introduction and roadmap
pyproject.toml             — build metadata (setuptools)
requirements.txt           — Python dependency pins
src/lang2mech_ir/          — Python package implementing IR, parser, auditor, etc.
tests/                     — unit and integration tests (to be filled incrementally)
```

## Getting started

1. Create a Python 3.10+ environment (conda or venv) and install `pip install -r requirements.txt`.
2. Run `pytest` to execute the parser/auditor/LLM-interface/controller/pipeline/metrics/MuJoCo unit tests.

### Optional: hooking up a real Claude API

The `LLMInterface` can call Anthropic Claude models when you supply credentials:

1. Install the `anthropic` package (already listed in `requirements.txt`).
2. Export your key: `export ANTHROPIC_API_KEY=sk-ant-...` (never hard-code the key in source control).
3. Instantiate the interface with `use_remote=True`, e.g.:

   ```python
   from lang2mech_ir import LLMInterface

   interface = LLMInterface(use_remote=True, model="claude-3-5-sonnet-20240620")
   ir = interface.compile("Slowly insert the 10 mm peg ...")
   ```

If the API call fails (missing key, network issue, etc.), the class automatically falls back to the local heuristic parser so your workflow does not break while offline.

## Contributing roadmap

The build follows the steps in the research plan. We now have IR/schema/auditing, a simplified MPC + simulator, MuJoCo scaffolding, and end-to-end logging/metrics. Next milestones cover full MuJoCo execution, richer monitoring dashboards, and the experiments/reporting artifacts.

## MuJoCo demo model

- A minimal slider-based peg-in-hole MJCF is provided in `assets/peg_in_hole.xml`. It exposes a single `slide_z` joint with a `slide_motor` actuator so the MPC outputs can directly drive the insertion axis.
- After `pip install mujoco`, you can run a MuJoCo-backed episode with:

-  ```bash
-  PYTHONPATH=src python - <<'PY'
-  from pathlib import Path
-  from lang2mech_ir import MechanicsIR
-  from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode
-
-  ir = MechanicsIR()
-  ir.hole.depth_m = 0.05
-  ir.max_force.maximum = 10.0
-  log = run_mujoco_episode(ir, Path("assets/peg_in_hole.xml"))
-  print(f"Episode steps: {len(log.times_s)} Final depth: {log.positions_m[-1]:.3f} m")
-  PY
-  ```
- To plug in your own robot/scene, edit the MJCF path plus joint/actuator names in `MujocoPegInHoleConfig`.
- A ready-to-run multi-DoF Panda example (requires `mujoco_menagerie-main/franka_emika_panda/`) is available:

  ```bash
  PYTHONPATH=src python scripts/run_panda_mujoco.py
  ```
