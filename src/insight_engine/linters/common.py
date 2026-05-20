"""Linter helpers."""

from __future__ import annotations

from typing import Any

from insight_engine.harness.state import utc_now_iso


def lint_result(
    stage_name: str,
    passed: bool,
    issues: list[str],
    metrics: dict[str, Any],
    retryable: bool,
) -> dict[str, Any]:
    """返回统一 stage gate / linter 结果。"""
    return {
        "stage": stage_name,
        "passed": passed,
        "issues": issues,
        "metrics": metrics,
        "retryable": retryable,
        "checked_at": utc_now_iso(),
    }
