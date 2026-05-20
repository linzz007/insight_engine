"""对话 Agent 的最小意图路由。

V1 先用可解释的关键词规则判断是否调用 daily_news_report_skill。
后续如果要改成 LLM intent classifier，只需要替换 `detect_intent`，
不需要改日报 Skill 内部的 graph/state。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from insight_engine.skill_executors.daily_news_report import (
    DailyNewsReportResult,
    format_daily_news_report_result,
    run_daily_news_report_skill,
)


IntentName = Literal["daily_news_report", "chat"]

DAILY_REPORT_KEYWORDS = [
    "今日新闻分析报告",
    "新闻分析报告",
    "今日新闻",
    "新闻日报",
    "ai日报",
    "AI日报",
    "生成日报",
    "生成报告",
    "日报",
    "新闻报告",
]


@dataclass(frozen=True)
class ConversationResponse:
    """对话层统一返回对象。"""

    intent: IntentName
    message: str
    artifacts: dict[str, str | None] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    skill_result: DailyNewsReportResult | None = None


def detect_intent(message: str) -> IntentName:
    """判断用户消息是否在请求生成今日新闻分析报告。"""
    normalized = message.strip().lower()
    if any(keyword.lower() in normalized for keyword in DAILY_REPORT_KEYWORDS):
        return "daily_news_report"
    return "chat"


def handle_message(message: str, *, show_summary: bool = False) -> ConversationResponse:
    """处理一条页面对话消息。"""
    intent = detect_intent(message)
    if intent == "daily_news_report":
        result = run_daily_news_report_skill()
        state = result.state
        return ConversationResponse(
            intent=intent,
            message=format_daily_news_report_result(result, include_summary=show_summary),
            artifacts={
                "report": result.report_path,
                "report_html": result.report_html_path,
                "chart_html": result.chart_path,
                "pipeline_summary": result.pipeline_summary_path,
                "pipeline_summary_json": result.summary_paths.get("json"),
                "run_artifact": result.run_artifact_path,
            },
            summary={
                "run_id": state.run_id,
                "final_stage": state.current_stage,
                "quality_passed": state.final_quality_result.get("passed"),
                "global_raw_items": len(state.global_raw_items),
                "ai_raw_items": len(state.ai_raw_items),
                "global_structured_events": len(state.global_structured_events),
                "ai_structured_events": len(state.ai_structured_events),
                "errors": state.errors,
                "warnings": state.warnings,
            },
            skill_result=result,
        )

    return ConversationResponse(
        intent="chat",
        message=(
            "这是 Daily AI Insight Engine 的对话入口。"
            "普通问题会在这里正常回答；如果你说“生成今日新闻分析报告”，"
            "系统会调用 daily_news_report_skill 并返回报告、图表和流程摘要路径。"
        ),
    )
