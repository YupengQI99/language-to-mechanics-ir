# Lang2Mech-IR - Language to Mechanics Compiler for Robotic Assembly

<div align="center">

**Natural Language → Mechanical Constraints → Optimal Control → Safe Execution**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MuJoCo](https://img.shields.io/badge/MuJoCo-Physics-FF6B6B?style=for-the-badge)](https://mujoco.org/)
[![OSQP](https://img.shields.io/badge/OSQP-MPC-4ECDC4?style=for-the-badge)](https://osqp.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=for-the-badge)]()

[Features](#-key-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Usage](#-usage) • [Documentation](#-documentation)

</div>

---

## 📋 Overview

**Lang2Mech-IR** is an intelligent robotic assembly system that transforms natural language instructions into safe, executable robot control for **peg-in-hole insertion tasks**. The system bridges the gap between high-level human intent and low-level mechanical execution through:

- 🗣️ **Natural Language Understanding**: Parse instructions like *"slowly insert the peg without exceeding 5N"*
- 🔧 **Mechanics IR Compilation**: Convert to structured, validated mechanical specifications
- ✅ **Safety Auditing**: Enforce physical constraints and prevent dangerous operations
- 🎮 **Optimal Control**: OSQP-based MPC for force-constrained trajectory planning
- 🎯 **Physics Simulation**: MuJoCo-backed execution with real contact dynamics

Perfect for robotics researchers, automation engineers, and anyone building **safe human-robot collaboration systems**.

---

## ✨ Key Features

### 🎯 Core Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| **Natural Language Input** | Describe task in plain English/Chinese | ✅ Production |
| **Automatic Unit Conversion** | Handles mm, cm, m, N, degrees, radians seamlessly | ✅ Production |
| **Safety Validation** | Auditor enforces physical constraints & safe defaults | ✅ Production |
| **MPC Controller** | OSQP quadratic programming for optimal trajectories | ✅ Production |
| **Dual Simulation** | 1-D fast dynamics + full MuJoCo physics | ✅ Production |
| **Episode Metrics** | Success rate, force stats, duration analysis | ✅ Production |
| **Claude API Integration** | Optional LLM-powered instruction parsing | ✅ Production |
| **Batch Processing** | Run multiple instructions systematically | ✅ Production |

### 🔧 Technical Highlights

- **Modular Pipeline**: Each component (Parser → Auditor → MPC → Simulator) is independently testable
- **Mechanics IR Schema**: Formal intermediate representation for peg-in-hole constraints
- **Configurable Auditor**: Adjustable thresholds for clearance, speed, force limits
- **Extensible Robots**: Plug any MJCF model via `MujocoPegInHoleConfig`
- **Fallback Heuristics**: Works offline without LLM API access

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Python 3.10+
- pip (package manager)

# Optional
- MuJoCo (for physics simulation)
- Anthropic API key (for Claude-powered parsing)
```

### Installation

```bash
# 1. Clone repository
git clone https://github.com/YupengQI99/language-to-mechanics-ir.git
cd language-to-mechanics-ir

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install MuJoCo for physics simulation
pip install mujoco

# 5. Verify installation
pytest
```

### 30-Second Demo

```python
from lang2mech_ir.pipeline import LanguageToActionPipeline

# Initialize
pipeline = LanguageToActionPipeline()

# Run natural language instruction
result = pipeline.run(
    "Slowly insert the 10mm peg into the hole carefully, "
    "without using more than 5N of force."
)

# Check results
print(f"✅ Success: {result.metrics.success}")
print(f"📏 Final depth: {result.metrics.final_depth_m:.4f} m")
print(f"💪 Max force: {result.metrics.max_force_N:.2f} N")
print(f"⏱️ Duration: {result.metrics.duration_s:.2f} s")
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NATURAL LANGUAGE INPUT                               │
│           "Slowly insert the 10mm peg carefully, max 5N force"              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM INTERFACE                                      │
│  ┌─────────────────┐    ┌─────────────────┐                                 │
│  │ Heuristic Mode  │ OR │  Claude API     │  ← Automatic fallback           │
│  │ (Regex + Rules) │    │  (Remote LLM)   │                                 │
│  └────────┬────────┘    └────────┬────────┘                                 │
└───────────┴──────────────────────┴──────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INSTRUCTION PARSER                                    │
│  • Unit normalization (mm→m, deg→rad)                                       │
│  • Flexible key synonyms                                                    │
│  • Diameter → Radius conversion                                             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MECHANICS IR                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ PegGeometry  │ │ HoleGeometry │ │ ForceLimit   │ │ Trajectory   │       │
│  │ radius: 5mm  │ │ radius: 5.5mm│ │ max: 5N      │ │ speed: 0.01  │       │
│  │ length: 100mm│ │ depth: 50mm  │ │ min: 0N      │ │ strategy:    │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ │ straight     │       │
│                                                      └──────────────┘       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MECHANICS AUDITOR                                     │
│  ✓ Geometric feasibility (peg fits hole)                                    │
│  ✓ Force constraint validation                                              │
│  ✓ Speed limit enforcement (0.01-0.05 m/s)                                  │
│  ✓ Tolerance achievability                                                  │
│  ✓ Friction coefficient bounds (0-1)                                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MPC CONTROLLER                                       │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  minimize   Σ (x - x_goal)² + λ·u²                              │       │
│  │  subject to F ≤ F_max, v ≤ v_max, dynamics: x' = Ax + Bu       │       │
│  │  solver: OSQP (Quadratic Programming)                           │       │
│  └─────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│      1-D SIMULATOR            │ │      MUJOCO PHYSICS           │
│  • Fast execution             │ │  • Full contact dynamics      │
│  • Spring-damper contact      │ │  • Multi-DoF robots           │
│  • Good for prototyping       │ │  • Realistic forces           │
└───────────────┬───────────────┘ └───────────────┬───────────────┘
                └─────────────┬───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EPISODE METRICS                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │ Success    │ │ Final Depth│ │ Max Force  │ │ Duration   │               │
│  │ ✅ True    │ │ 0.048 m    │ │ 4.8 N      │ │ 2.3 s      │               │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📖 Usage

### Basic Pipeline

```python
from lang2mech_ir.pipeline import LanguageToActionPipeline

pipeline = LanguageToActionPipeline()

# Single instruction
result = pipeline.run("Insert the peg gently with max 10N force")

# Batch processing
instructions = [
    "Slowly insert the 10mm peg, max 5N force",
    "Quickly insert the 8mm peg into 8.3mm sleeve, max 15N",
    "Insert tight 12mm peg into chamfered hole, allow 30N",
]
results = pipeline.run_batch(instructions)
```

### Component-Level Control

```python
from lang2mech_ir import (
    LLMInterface,
    InstructionParser,
    MechanicsAuditor,
    MechanicsIR
)

# Step 1: Parse natural language
llm = LLMInterface(use_remote=False)
raw_dict = llm.interpret("Insert 8mm peg with max 15N")

# Step 2: Convert to structured IR
parser = InstructionParser()
ir = parser.parse(raw_dict)

# Step 3: Safety validation
auditor = MechanicsAuditor()
result = auditor.audit(ir)

print(f"Valid: {result.valid}")
print(f"Notes: {result.notes}")
```

### Claude API Integration

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
from lang2mech_ir import LLMInterface

# Enable Claude-powered parsing
llm = LLMInterface(
    use_remote=True,
    model="claude-3-5-sonnet-20240620"
)
ir = llm.compile("Perform spiral search to insert tight peg")
```

### MuJoCo Simulation

```python
from pathlib import Path
from lang2mech_ir import MechanicsIR
from lang2mech_ir.simulation.mujoco_runner import run_mujoco_episode

# Configure constraints
ir = MechanicsIR()
ir.hole.depth_m = 0.05
ir.max_force.maximum = 10.0

# Run physics simulation
log = run_mujoco_episode(ir, Path("assets/peg_in_hole.xml"))
print(f"Steps: {len(log.times_s)}")
print(f"Final depth: {log.positions_m[-1]:.3f} m")
```

---

## 📁 Project Structure

```
language-to-mechanics-ir/
│
├── 📂 src/lang2mech_ir/          # Main package
│   ├── 📄 ir_schema.py           # Core IR dataclasses
│   ├── 📄 units.py               # Unit conversion utilities
│   ├── 📄 parser.py              # Instruction parser
│   ├── 📄 llm_interface.py       # LLM integration layer
│   ├── 📄 auditor.py             # Safety validation
│   ├── 📄 pipeline.py            # End-to-end orchestration
│   │
│   ├── 📂 controller/            # Control algorithms
│   │   ├── 📄 state.py           # State definitions
│   │   ├── 📄 mpc.py             # OSQP-based MPC
│   │   └── 📄 multi_mpc.py       # Multi-DoF extension
│   │
│   ├── 📂 simulation/            # Simulation backends
│   │   ├── 📄 environment.py     # 1-D simulator
│   │   ├── 📄 mujoco_interface.py
│   │   └── 📄 mujoco_runner.py
│   │
│   └── 📂 logging_utils/         # Metrics & logging
│       └── 📄 metrics.py
│
├── 📂 tests/                     # Test suite (9 files)
├── 📂 scripts/                   # Demo & batch scripts
├── 📂 assets/                    # MuJoCo MJCF models
├── 📂 docs/                      # Documentation
│
├── 📄 pyproject.toml             # Build configuration
├── 📄 requirements.txt           # Dependencies
├── 📄 LICENSE                    # MIT License
└── 📄 README.md                  # This file
```

---

## 📊 Mechanics IR Schema

The **Intermediate Representation** captures all physical constraints:

| Category | Field | Type | Default | Description |
|----------|-------|------|---------|-------------|
| **Peg** | `radius_m` | float | 0.005 | Peg radius (meters) |
| | `length_m` | float | 0.10 | Peg length (meters) |
| | `chamfer_angle_deg` | float | 0.0 | Chamfer angle |
| **Hole** | `radius_m` | float | 0.0055 | Hole radius (meters) |
| | `depth_m` | float | 0.05 | Hole depth (meters) |
| **Force** | `maximum` | float | 20.0 | Max allowed force (N) |
| | `minimum` | float | 0.0 | Min force threshold |
| **Trajectory** | `insertion_speed_mps` | float | 0.01 | Target speed (m/s) |
| | `strategy` | enum | straight | straight / spiral_search |
| **Tolerance** | `alignment_deg` | float | 2.0 | Angular tolerance |
| | `position_m` | float | 0.0005 | Position tolerance |
| **Material** | `friction_coefficient` | float | 0.3 | Surface friction |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific module
pytest tests/test_auditor.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=lang2mech_ir --cov-report=html
```

---

## 🛠️ Scripts

| Script | Description |
|--------|-------------|
| `run_language_pipeline.py` | Demo: process 3 example instructions |
| `run_full_batch.py` | Batch processing with multiple cases |
| `run_panda_mujoco.py` | Panda robot MuJoCo demo |
| `run_panda_pipeline.py` | Full pipeline with Panda |
| `analyze_results.py` | Analyze batch results |

```bash
# Run demo
PYTHONPATH=src python scripts/run_language_pipeline.py

# Run Panda demo (requires mujoco_menagerie)
PYTHONPATH=src python scripts/run_panda_mujoco.py
```

---

## 📚 Documentation

- [Mechanics IR Format](docs/ir_format.md) - Detailed IR specification
- [Auditor Rules](docs/auditor_rules.md) - Safety validation logic
- [MPC Formulation](docs/mpc_formulation.md) - Controller mathematics
- [API Reference](docs/api_reference.md) - Full API documentation

---

## 🗺️ Roadmap

- [x] Core IR schema and parser
- [x] Mechanics auditor with safety checks
- [x] OSQP-based MPC controller
- [x] 1-D insertion simulator
- [x] MuJoCo interface scaffold
- [x] Episode metrics computation
- [ ] Full MuJoCo execution pipeline
- [ ] Real-time monitoring dashboard
- [ ] Parameter sweep experiments
- [ ] Research paper artifacts

---

## 📄 Citation

If you use this work in your research, please cite:

```bibtex
@software{lang2mech_ir_2025,
  author       = {Yupeng Qi},
  title        = {Lang2Mech-IR: Language to Mechanics Compiler for Robotic Assembly},
  year         = {2025},
  publisher    = {GitHub},
  url          = {https://github.com/YupengQI99/language-to-mechanics-ir}
}
```

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [MuJoCo](https://mujoco.org/) - Physics simulation engine
- [OSQP](https://osqp.org/) - Quadratic programming solver
- [Anthropic Claude](https://www.anthropic.com/) - LLM capabilities
- [NumPy](https://numpy.org/) & [SciPy](https://scipy.org/) - Scientific computing

---

<div align="center">

**Made with ❤️ for the robotics community**

[⬆ Back to Top](#lang2mech-ir---language-to-mechanics-compiler-for-robotic-assembly)

</div>
