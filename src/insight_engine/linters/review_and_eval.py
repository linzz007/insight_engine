"""Linter for review_and_eval stage."""

from __future__ import annotations

from typing import Any

from insight_engine.harness.state import InsightEngineState
from insight_engine.linters.common import lint_result


def lint(state: InsightEngineState) -> dict[str, Any]:
    """检查最终质量 hook 是否写入结果。"""
    issues = []
    quality_result = state.final_quality_result
    if not quality_result:
        issues.append("final_quality_result 为空")
    if "passed" not in quality_result:
        issues.append("final_quality_result 缺少 passed 字段")
    return lint_result(
        "review_and_eval",
        not issues,
        issues,
        {
            "quality_passed": quality_result.get("passed"),
            "review_passed": state.review_result.get("passed"),
        },
        retryable=False,
    )
