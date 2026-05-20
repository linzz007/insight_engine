"""单阶段运行器。

用于只运行某一个 stage，同时仍然走 Harness Hook。
这适合调试某个阶段，比如只测试数据获取质量。
"""

from __future__ import annotations

import os

from insight_engine.harness.graph import StageHandler, StageName
from insight_engine.harness.hooks.stage_hooks import after_stage, before_stage
from insight_engine.harness.stage_gates import evaluate_stage_gate
from insight_engine.harness.state import InsightEngineState


def run_single_stage(
    state: InsightEngineState,
    stage_name: StageName,
    handler: StageHandler,
) -> InsightEngineState:
    """只运行一个 stage，并触发 before/after hook。"""
    state.mark_stage(stage_name)
    max_retry_count = int(os.getenv("HARNESS_STAGE_MAX_RETRY", "1"))

    while True:
        hook_context = before_stage(state, stage_name)
        try:
            state = handler(state)
        except Exception as exc:  # noqa: BLE001
            after_stage(state, hook_context, error=repr(exc))
            state.add_error(
                stage=stage_name,
                message="单阶段执行失败",
                detail=repr(exc),
            )
            state.mark_stage("failed")
            return state

        gate_result = evaluate_stage_gate(state, stage_name)
        state.add_stage_gate_result(gate_result)
        state = after_stage(state, hook_context)
        if gate_result.get("passed"):
            return state

        current_retry_count = state.stage_retry_counts.get(stage_name, 0)
        can_retry = bool(gate_result.get("retryable")) and current_retry_count < max_retry_count
        if not can_retry:
            state.add_error(
                stage=stage_name,
                message="stage gate 未通过",
                detail=gate_result,
            )
            state.mark_stage("failed")
            return state

        retry_count = state.increment_stage_retry(stage_name)
        state.add_warning(
            stage=stage_name,
            message=f"stage gate 未通过，重跑当前 stage：第 {retry_count} 次",
            detail=gate_result,
        )
