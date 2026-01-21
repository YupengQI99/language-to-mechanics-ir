"""Run the LanguageToActionPipeline on a demo instruction set."""

from __future__ import annotations

import json
from pathlib import Path

from lang2mech_ir.pipeline import LanguageToActionPipeline

INSTRUCTIONS = [
    "Slowly insert the 10 mm peg that is 100 mm long into the hole carefully, without using more than 5 N of force.",
    "Perform a spiral search to insert the 8 mm peg into the 8.3 mm sleeve, keep forces under 15 N and finish within 6 seconds.",
    "Quickly insert the dry 12 mm peg into the chamfered 12.2 mm hole, allow up to 30 N force but maintain 0.5 degree alignment tolerance.",
]


def main() -> None:
    pipeline = LanguageToActionPipeline()
    results = pipeline.run_batch(INSTRUCTIONS)

    summary = []
    for res in results:
        summary.append(
            {
                "instruction": res.instruction,
                "max_force": res.ir.max_force.maximum,
                "alignment_deg": res.ir.tolerances.alignment_deg,
                "success": res.metrics.success,
                "final_depth_m": res.metrics.final_depth_m,
                "goal_depth_m": res.metrics.goal_depth_m,
                "final_force_N": res.metrics.final_force_N,
                "duration_s": res.metrics.duration_s,
            }
        )

    output_path = Path("results/language_pipeline.json")
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} with {len(summary)} entries.")
    for entry in summary:
        print(
            f"- Instruction: {entry['instruction'][:80]}...\n"
            f"  success={entry['success']} final_depth={entry['final_depth_m']:.4f} m "
            f"force={entry['final_force_N']:.2f} N duration={entry['duration_s']:.2f} s"
        )


if __name__ == "__main__":  # pragma: no cover - manual script
    main()
