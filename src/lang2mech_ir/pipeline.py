"""End-to-end pipeline: instruction -> IR -> audit -> MPC simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from . import InstructionParser, MechanicsAuditor, LLMInterface
from .controller import PegInHoleState, ControllerConfig
from .simulation.environment import SimpleInsertionSimulator, SimulationConfig, EpisodeLog
from .logging_utils import EpisodeMetrics, compute_metrics
from .ir_schema import MechanicsIR


@dataclass
class PipelineResult:
    instruction: str
    ir: MechanicsIR
    audit_notes: List[str]
    episode_log: EpisodeLog
    metrics: EpisodeMetrics


@dataclass
class LanguageToActionPipeline:
    """Convenience orchestrator for the full research-plan pipeline."""

    controller_config: ControllerConfig = field(default_factory=ControllerConfig)
    use_remote_llm: bool = False

    def __post_init__(self) -> None:
        self.parser = InstructionParser()
        self.interface = LLMInterface(parser=self.parser, use_remote=self.use_remote_llm)
        self.auditor = MechanicsAuditor()
        sim_config = SimulationConfig(controller=self.controller_config)
        self.simulator = SimpleInsertionSimulator(sim_config)

    def process_instruction(self, instruction: str) -> PipelineResult:
        ir = self.interface.compile(instruction)
        audit = self.auditor.audit(ir)
        initial_state = PegInHoleState(position_m=0.0, velocity_mps=0.0, depth_goal_m=ir.hole.depth_m)
        log = self.simulator.run_episode(audit.corrected_ir, initial_state)
        metrics = compute_metrics(audit.corrected_ir, log)
        return PipelineResult(
            instruction=instruction,
            ir=audit.corrected_ir,
            audit_notes=audit.observations,
            episode_log=log,
            metrics=metrics,
        )

    def run_batch(self, instructions: Iterable[str]) -> List[PipelineResult]:
        return [self.process_instruction(text) for text in instructions]
