"""规则型质量检查工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from insight_engine.harness.state import (
    REPORT_REQUIRED_HEADINGS as REQUIRED_REPORT_HEADINGS,
    STRUCTURED_EVENT_FIELD_SPEC,
)


REQUIRED_EVENT_FIELDS = [
    key for key, spec in STRUCTURED_EVENT_FIELD_SPEC.items() if spec.get("required")
]


def check_quality(
    raw_items: list[dict[str, Any]],
    cleaned_items: list[dict[str, Any]],
    structured_events: list[dict[str, Any]],
    analysis_result: dict[str, Any],
    report_paths: dict[str, str],
) -> dict[str, Any]:
    """执行最终质量检查。"""
    issues: list[dict[str, Any]] = []

    if len(raw_items) < 10:
        issues.append(_issue("raw_items", "原始数据少于 10 条", "collect_raw_items"))

    if len(cleaned_items) < 10:
        issues.append(_issue("cleaned_items", "清洗后数据少于 10 条", "clean_items"))

    if len(structured_events) < 10:
        issues.append(_issue("structured_events", "结构化记录少于 10 条", "structure_events"))

    for index, event in enumerate(structured_events):
        missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
        if missing:
            issues.append(
                _issue(
                    "structured_events",
                    f"第 {index + 1} 条结构化记录缺少字段：{missing}",
                    "structure_events",
                )
            )

    if not analysis_result.get("top_events"):
        issues.append(_issue("analysis_result", "缺少 Top 事件", "analyze_insights"))

    if not analysis_result.get("trend_judgment"):
        issues.append(_issue("analysis_result", "缺少趋势判断", "analyze_insights"))

    report_path = report_paths.get("report")
    report_html_path = report_paths.get("report_html")
    chart_html_path = report_paths.get("chart_html")
    chart_data_path = report_paths.get("chart_data")

    if not report_path or not Path(report_path).exists():
        issues.append(_issue("report", "报告文件不存在", "generate_report"))
    else:
        report_text = Path(report_path).read_text(encoding="utf-8")
        for heading in REQUIRED_REPORT_HEADINGS:
            if heading not in report_text:
                issues.append(_issue("report", f"报告缺少章节：{heading}", "generate_report"))

    if not chart_html_path or not Path(chart_html_path).exists():
        issues.append(_issue("chart_html", "HTML 图表文件不存在", "generate_report"))

    if not report_html_path or not Path(report_html_path).exists():
        issues.append(_issue("report_html", "HTML 报告文件不存在", "generate_report"))

    if not chart_data_path or not Path(chart_data_path).exists():
        issues.append(_issue("chart_data", "图表数据文件不存在", "generate_report"))

    retry_stage = issues[0]["retry_stage"] if issues else None
    return {
        "passed": not issues,
        "score": max(0, 100 - len(issues) * 10),
        "issues": issues,
        "retry_stage": retry_stage,
    }


def _issue(target: str, message: str, retry_stage: str) -> dict[str, str]:
    return {
        "target": target,
        "message": message,
        "retry_stage": retry_stage,
    }
