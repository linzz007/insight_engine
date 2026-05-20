"""Review stage.

V1 使用最终质量 hook，并生成一个简单 reviewer 结果。
"""

from __future__ import annotations

from insight_engine.harness.artifacts import write_json_artifact
from insight_engine.harness.hooks.final_quality_hook import run_final_quality_hook
from insight_engine.harness.state import InsightEngineState


def review_and_eval(state: InsightEngineState) -> InsightEngineState:
    """执行最终质量 hook，并写入 review_result / final_quality_result。"""
    quality_result = run_final_quality_hook(state)

    state.final_quality_result = quality_result
    state.review_result = {
        "passed": quality_result["passed"],
        "score": quality_result["score"],
        "issues": quality_result["issues"],
        "retry_stage": quality_result["retry_stage"],
    }

    write_json_artifact(
        state=state,
        artifact_name="final_quality_hook",
        data={
            "run_id": state.run_id,
            "target_date": state.target_date,
            "review_result": state.review_result,
            "final_quality_result": state.final_quality_result,
        },
        base_dir="outputs/reports",
        filename="final_quality_hook.json",
    )

    return state
