from insight_engine.harness.graph import build_graph
from insight_engine.harness.state import InsightEngineState


def _passing_gate(state: InsightEngineState, stage_name: str) -> dict:
    return {
        "stage": stage_name,
        "passed": True,
        "issues": [],
        "metrics": {},
        "retryable": False,
    }


def test_graph_fails_when_raw_items_are_empty(monkeypatch):
    monkeypatch.setattr("insight_engine.harness.graph.evaluate_stage_gate", _passing_gate)
    graph = build_graph(handlers={"collect_raw_items": lambda state: state})

    state = graph.run(InsightEngineState())

    assert state.current_stage == "failed"
    assert state.errors == []


def test_graph_runs_to_done_with_minimum_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr("insight_engine.harness.graph.evaluate_stage_gate", _passing_gate)

    def collect_raw_items(state: InsightEngineState) -> InsightEngineState:
        state.raw_items = [{"title": "AI news"}]
        return state

    def clean_items(state: InsightEngineState) -> InsightEngineState:
        state.cleaned_items = state.raw_items
        return state

    def structure_events(state: InsightEngineState) -> InsightEngineState:
        state.structured_events = [
            {
                "id": "event_1",
                "source_scope": "ai",
                "title": "AI news",
                "source_name": "test_source",
                "source_type": "test",
                "url": "https://example.com/news",
                "published_at": "2026-05-19T00:00:00+00:00",
                "industry_area": "ai_app",
                "topic_tags": ["ai"],
                "hotness_score": 80,
                "importance_level": "high",
                "summary": "AI news summary",
                "key_entities": ["AI"],
                "impact_analysis": "impact",
                "risk_or_opportunity": "risk",
                "evidence": {"source_url": "https://example.com/news"},
                "raw_ref": "clean_ai_1",
            }
        ]
        return state

    def analyze_insights(state: InsightEngineState) -> InsightEngineState:
        state.analysis_result = {
            "summary": "summary",
            "global_top_events": [],
            "top_events": [{"id": "event_1", "title": "AI news"}],
            "trend_judgment": {
                "technology": "tech",
                "application": "app",
                "policy": "policy",
                "capital": "capital",
            },
            "risk_or_opportunity_notes": [],
            "stats": {},
        }
        return state

    def generate_report(state: InsightEngineState) -> InsightEngineState:
        report_path = tmp_path / "demo.md"
        chart_path = tmp_path / "charts.html"
        report_path.write_text(
            "\n".join(
                [
                    "## 数据源概览",
                    "## 全球热点背景",
                    "## 今日 AI 领域主要热点",
                    "## 重要事件深度总结",
                    "## 趋势判断",
                    "## 风险和机会提示",
                    "## 结构化数据附录",
                    "## 质量评估摘要",
                ]
            ),
            encoding="utf-8",
        )
        chart_path.write_text("<html></html>", encoding="utf-8")
        state.report_paths = {"report": str(report_path), "chart_html": str(chart_path)}
        return state

    def review_and_eval(state: InsightEngineState) -> InsightEngineState:
        state.review_result = {"passed": True}
        state.final_quality_result = {"passed": True}
        return state

    graph = build_graph(
        handlers={
            "collect_raw_items": collect_raw_items,
            "clean_items": clean_items,
            "structure_events": structure_events,
            "analyze_insights": analyze_insights,
            "generate_report": generate_report,
            "review_and_eval": review_and_eval,
        }
    )

    state = graph.run(InsightEngineState())

    assert state.current_stage == "done"
    assert state.raw_items
    assert state.cleaned_items
    assert state.structured_events
    assert state.analysis_result
    assert state.report_paths
