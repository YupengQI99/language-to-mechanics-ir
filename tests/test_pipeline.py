from lang2mech_ir.pipeline import LanguageToActionPipeline


def test_pipeline_runs_single_instruction():
    pipeline = LanguageToActionPipeline()
    instruction = "Insert the 6 mm peg carefully, max force 6 N."
    result = pipeline.process_instruction(instruction)

    assert result.ir.max_force.maximum == 6.0
    assert len(result.audit_notes) >= 1
    assert len(result.episode_log.times_s) >= 1
    assert result.metrics.goal_depth_m == result.ir.hole.depth_m
