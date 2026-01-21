# Language-to-Mechanics IR Compiler

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

A modular system that converts **natural language instructions** into **executable robot control constraints** for peg-in-hole assembly tasks. The pipeline transforms high-level commands like *"slowly insert the peg without exceeding 5N force"* into validated mechanical specifications and optimal control sequences.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Natural Language Input                               │
│              "Slowly insert the 10mm peg carefully, max 5N force"           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      LLM Interface        │  Heuristic + Claude API
                    │    (llm_interface.py)     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Instruction Parser    │  Unit normalization
                    │       (parser.py)         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      Mechanics IR         │  Structured constraints
                    │      (ir_schema.py)       │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Mechanics Auditor      │  Safety validation
                    │      (auditor.py)         │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     MPC Controller        │  OSQP optimization
                    │   (controller/mpc.py)     │
                    └─────────────┬─────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
    ┌─────────▼─────────┐                 ┌──────────▼──────────┐
    │   1-D Simulator   │                 │   MuJoCo Physics    │
    │  (environment.py) │                 │ (mujoco_interface)  │
    └─────────┬─────────┘                 └──────────┬──────────┘
              │                                       │
              └───────────────────┬───────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    Episode Metrics        │  Success/Force/Duration
                    │      (metrics.py)         │
                    └───────────────────────────┘
```

## Features

- **Natural Language Understanding**: Parse instructions like "insert quickly", "handle carefully", "maximum 10N force"
- **Automatic Unit Conversion**: Handles mixed units (mm, cm, m, N, degrees, radians)
- **Safety Validation**: Auditor enforces physical constraints and safe defaults
- **Optimal Control**: OSQP-based MPC for force-constrained trajectory planning
- **Dual Simulation**: Simple 1-D dynamics or full MuJoCo physics
- **Extensible**: Plug in custom robot models via MJCF

## Installation

### Requirements
- Python 3.10+
- MuJoCo (optional, for physics simulation)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/YupengQI99/language-to-mechanics-ir.git
cd language-to-mechanics-ir

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Optional: MuJoCo Support

```bash
pip install mujoco
```

## Usage

### Basic Pipeline

```python
from lang2mech_ir.pipeline import LanguageToActionPipeline

# Initialize pipeline
pipeline = LanguageToActionPipeline()

# Process natural language instruction
instruction = "Slowly insert the 10mm peg into the hole carefully, without using more than 5N of force."
result = pipeline.run(instruction)

# Access results
print(f"Success: {result.metrics.success}")
print(f"Final depth: {result.metrics.final_depth_m:.4f} m")
print(f"Max force: {result.metrics.max_force_N:.2f} N")
```

### Component-Level Usage

```python
from lang2mech_ir import LLMInterface, InstructionParser, MechanicsAuditor, MechanicsIR

# Step 1: Parse natural language
llm = LLMInterface(use_remote=False)  # Use heuristic parser
raw_dict = llm.interpret("Insert the 8mm peg with max 15N force")

# Step 2: Convert to structured IR
parser = InstructionParser()
ir = parser.parse(raw_dict)

# Step 3: Validate and correct
auditor = MechanicsAuditor()
audit_result = auditor.audit(ir)

print(f"Valid: {audit_result.valid}")
print(f"Corrected IR: {audit_result.corrected_ir}")
print(f"Notes: {audit_result.notes}")
```

### Using Claude API

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
from lang2mech_ir import LLMInterface

# Enable remote Claude API
interface = LLMInterface(use_remote=True, model="claude-3-5-sonnet-20240620")
ir = interface.compile("Perform spiral search to insert the tight peg")
```

### MuJoCo Simulation

```python
from pathlib import Path
from lang2mech_ir import MechanicsIR
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

# Configure IR
ir = MechanicsIR()
ir.hole.depth_m = 0.05
ir.max_force.maximum = 10.0

# Run simulation
log = run_mujoco_episode(ir, Path("assets/peg_in_hole.xml"))
print(f"Steps: {len(log.times_s)}, Final depth: {log.positions_m[-1]:.3f} m")
```

## Project Structure

```
language-to-mechanics-ir/
├── src/lang2mech_ir/
│   ├── ir_schema.py          # Core dataclasses (MechanicsIR, PegGeometry, etc.)
│   ├── units.py              # Unit conversion utilities
│   ├── parser.py             # Instruction parser with unit normalization
│   ├── llm_interface.py      # LLM integration (heuristic + Claude API)
│   ├── auditor.py            # Safety validation and constraint checking
│   ├── pipeline.py           # End-to-end orchestration
│   ├── controller/
│   │   ├── state.py          # State and config dataclasses
│   │   ├── mpc.py            # OSQP-based MPC controller
│   │   └── multi_mpc.py      # Multi-DoF extension
│   ├── simulation/
│   │   ├── environment.py    # 1-D insertion simulator
│   │   ├── mujoco_interface.py  # MuJoCo wrapper
│   │   └── mujoco_runner.py  # Episode execution
│   └── logging_utils/
│       └── metrics.py        # Performance metrics
├── tests/                    # Unit and integration tests
├── scripts/                  # Demo and batch execution scripts
├── assets/                   # MuJoCo MJCF models
└── docs/                     # Documentation
```

## Mechanics IR Schema

The Intermediate Representation captures all physical constraints:

| Field | Type | Description |
|-------|------|-------------|
| `peg.radius_m` | float | Peg radius in meters |
| `peg.length_m` | float | Peg length in meters |
| `hole.radius_m` | float | Hole radius in meters |
| `hole.depth_m` | float | Hole depth in meters |
| `max_force.maximum` | float | Maximum allowed force (N) |
| `trajectory.insertion_speed_mps` | float | Target speed (m/s) |
| `tolerances.alignment_deg` | float | Angular tolerance (degrees) |
| `material.friction_coefficient` | float | Surface friction |

## Auditor Safety Checks

The Mechanics Auditor validates:

- **Geometric feasibility**: Peg fits in hole with minimum clearance
- **Force constraints**: Bounds are physically meaningful
- **Speed limits**: Clamped to safe ranges (default: 0.01-0.05 m/s)
- **Tolerance enforcement**: Achievable alignment tolerances
- **Material properties**: Valid friction coefficients (0-1)

## Running Experiments

### Single Instruction
```bash
PYTHONPATH=src python scripts/run_language_pipeline.py
```

### Batch Processing
```bash
PYTHONPATH=src python scripts/run_full_batch.py
```

### Panda Robot Demo
```bash
PYTHONPATH=src python scripts/run_panda_mujoco.py
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auditor.py

# Run with coverage
pytest --cov=lang2mech_ir
```

## Citation

If you use this work in your research, please cite:

```bibtex
@software{lang2mech_ir,
  author = {Yupeng Qi},
  title = {Language-to-Mechanics IR Compiler},
  year = {2025},
  url = {https://github.com/YupengQI99/language-to-mechanics-ir}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [MuJoCo](https://mujoco.org/) for physics simulation
- [OSQP](https://osqp.org/) for quadratic programming
- [Anthropic Claude](https://www.anthropic.com/) for LLM capabilities
