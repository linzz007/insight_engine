"""Final quality hook.

这是最终阶段的 hook 操作：读取 State 中的全链路产物，执行规则型质量检查。
它和普通 stage gate 的区别是检查范围更大，目标是判断整条链路是否可交付。
"""

from __future__ import annotations

from insight_engine.harness.state import InsightEngineState
from insight_engine.tools.quality_check import check_quality


def run_final_quality_hook(state: InsightEngineState) -> dict:
    """执行最终质量检查。"""
    raw_items = state.global_raw_items + state.ai_raw_items
    cleaned_items = state.global_cleaned_items + state.ai_cleaned_items
    structured_events = state.global_structured_events + state.ai_structured_events

    result = check_quality(
        raw_items=raw_items or state.raw_items,
        cleaned_items=cleaned_items or state.cleaned_items,
        structured_events=structured_events or state.structured_events,
        analysis_result=state.analysis_result,
        report_paths=state.report_paths,
    )
    result["hook_name"] = "final_quality_hook"
    return result
