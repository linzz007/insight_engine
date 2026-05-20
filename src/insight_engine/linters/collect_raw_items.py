"""Linter for collect_raw_items stage."""

from __future__ import annotations

import os
from typing import Any

from insight_engine.harness.state import InsightEngineState
from insight_engine.linters.common import lint_result


def lint(state: InsightEngineState) -> dict[str, Any]:
    """检查 Stage 1 是否抓到最低数量的 global / AI 原始数据。"""
    min_global = int(os.getenv("HARNESS_MIN_GLOBAL_RAW", "5"))
    min_ai = int(os.getenv("HARNESS_MIN_AI_RAW", "3"))
    issues = []
    if len(state.global_raw_items) < min_global:
        issues.append(f"global_raw_items 数量不足：{len(state.global_raw_items)} < {min_global}")
    if len(state.ai_raw_items) < min_ai:
        issues.append(f"ai_raw_items 数量不足：{len(state.ai_raw_items)} < {min_ai}")
    return lint_result(
        "collect_raw_items",
        not issues,
        issues,
        {
            "global_raw_items": len(state.global_raw_items),
            "ai_raw_items": len(state.ai_raw_items),
            "min_global_raw": min_global,
            "min_ai_raw": min_ai,
        },
        retryable=True,
    )
