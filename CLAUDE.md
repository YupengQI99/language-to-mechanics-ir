# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Language-to-Mechanics IR Compiler: converts natural language peg-in-hole instructions into executable robot control constraints. Pipeline: Language → LLM Interface → Parser → MechanicsIR → Auditor → MPC Controller → Simulator → Metrics.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a single test file
pytest tests/test_auditor.py

# Run a specific test
pytest tests/test_auditor.py::test_audit_clamps_speed -v

# Run with PYTHONPATH for scripts
PYTHONPATH=src python scripts/run_language_pipeline.py

# Run MuJoCo Panda demo (requires mujoco package)
PYTHONPATH=src python scripts/run_panda_mujoco.py
```

## Architecture

```
src/lang2mech_ir/
├── ir_schema.py          # Core dataclasses: MechanicsIR, PegGeometry, HoleGeometry, etc.
├── units.py              # Unit conversion: length_to_m(), angle_to_deg(), force_to_newtons()
├── parser.py             # InstructionParser: dict → MechanicsIR with unit normalization
├── llm_interface.py      # LLMInterface: natural language → dict (heuristic + Claude API)
├── auditor.py            # MechanicsAuditor: validates IR, enforces safe defaults
├── pipeline.py           # LanguageToActionPipeline: end-to-end orchestrator
├── controller/
│   ├── state.py          # PegInHoleState, ControllerConfig dataclasses
│   ├── mpc.py            # PegInHoleMPC: OSQP-based optimal control
│   └── multi_mpc.py      # Multi-DoF MPC extension
├── simulation/
│   ├── environment.py    # SimpleInsertionSimulator: 1-D dynamics with contact
│   ├── mujoco_interface.py  # MujocoPegInHoleEnv: thin MuJoCo wrapper
│   └── mujoco_runner.py  # run_mujoco_episode(): full episode execution
└── logging_utils/
    └── metrics.py        # compute_metrics(): EpisodeMetrics from episode logs
```

**Data Flow:**
1. `LLMInterface.interpret(instruction)` → raw dict (via heuristic or Claude API)
2. `InstructionParser.parse(dict)` → `MechanicsIR` with normalized units
3. `MechanicsAuditor.audit(ir)` → `AuditResult` (valid flag, corrected IR, notes)
4. Simulator runs episode using MPC → `EpisodeLog`
5. `compute_metrics(log, ir)` → `EpisodeMetrics` (success, depth, force stats)

## Key Classes

- **MechanicsIR**: Root schema containing peg/hole geometry, materials, trajectory, tolerances, force/time limits
- **InstructionParser**: Handles flexible key synonyms, diameter→radius conversion, strategy parsing
- **MechanicsAuditor**: Configurable thresholds (`min_clearance_m`, `conservative_speed_mps`, `max_alignment_deg`)
- **LLMInterface**: `use_remote=True` calls Claude API; falls back to heuristic on failure
- **PegInHoleMPC**: Uses OSQP solver with double-integrator dynamics model

## Environment Variables

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # Required for LLMInterface(use_remote=True)
```

## Testing Notes

- pytest is configured with `pythonpath = ["src"]` in pyproject.toml
- MuJoCo tests require `pip install mujoco` (optional dependency)
- Tests use parametrized fixtures for multiple scenarios
