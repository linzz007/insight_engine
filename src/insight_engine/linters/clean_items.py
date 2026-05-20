"""Linter for clean_items stage."""

from __future__ import annotations

from typing import Any

from insight_engine.harness.state import InsightEngineState
from insight_engine.linters.common import lint_result


def lint(state: InsightEngineState) -> dict[str, Any]:
    """检查 Stage 2 清洗产物是否可被结构化阶段消费。"""
    issues = []
    all_items = state.global_cleaned_items + state.ai_cleaned_items
    if not all_items:
        issues.append("清洗后没有任何可用数据")

    missing_title = [item.get("id") for item in all_items if not item.get("title")]
    if missing_title:
        issues.append(f"存在缺少 title 的 cleaned item：{missing_title[:5]}")

    urls = [str(item.get("url")) for item in all_items if item.get("url")]
    duplicate_urls = sorted({url for url in urls if urls.count(url) > 1})
    if duplicate_urls:
        issues.append(f"存在重复 URL：{duplicate_urls[:5]}")

    return lint_result(
        "clean_items",
        not issues,
        issues,
        {
            "global_cleaned_items": len(state.global_cleaned_items),
            "ai_cleaned_items": len(state.ai_cleaned_items),
            "duplicate_url_count": len(duplicate_urls),
        },
        retryable=False,
    )
