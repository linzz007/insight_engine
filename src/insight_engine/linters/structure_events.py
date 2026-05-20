"""Linter for structure_events stage."""

from __future__ import annotations

from typing import Any

from insight_engine.harness.state import STRUCTURED_EVENT_FIELD_SPEC, InsightEngineState
from insight_engine.linters.common import lint_result


STRUCTURED_EVENT_REQUIRED_FIELDS = [
    key for key, spec in STRUCTURED_EVENT_FIELD_SPEC.items() if spec.get("required")
]


def lint(state: InsightEngineState) -> dict[str, Any]:
    """检查 Stage 3 结构化事件是否满足跨阶段合同。"""
    issues = []
    events = state.global_structured_events + state.ai_structured_events
    if not events:
        issues.append("结构化事件为空")
    for index, event in enumerate(events):
        missing = [field for field in STRUCTURED_EVENT_REQUIRED_FIELDS if field not in event]
        if missing:
            issues.append(f"event[{index}] 缺少字段：{missing}")
        score = event.get("hotness_score")
        if not isinstance(score, int) or score < 0 or score > 100:
            issues.append(f"event[{index}].hotness_score 必须是 0-100 整数")
    return lint_result(
        "structure_events",
        not issues,
        issues[:20],
        {
            "global_structured_events": len(state.global_structured_events),
            "ai_structured_events": len(state.ai_structured_events),
            "checked_events": len(events),
        },
        retryable=True,
    )
