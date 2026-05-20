# daily_news_report_skill

## 触发条件

当用户在页面聊天里表达“生成今日新闻分析报告”“今日新闻日报”“AI 日报”等意图时，对话 Agent 调用这个 Skill。

普通闲聊不调用本 Skill。

## 执行方式

本 Skill 不让 LLM 自由猜流程，而是启动 `src/insight_engine/skill_executors/daily_news_report.py` 中的 graph：

```text
collect_raw_items
-> clean_items
-> structure_events
-> analyze_insights
-> generate_report
-> review_and_eval
-> done/failed
```

graph 使用 `InsightEngineState` 保存每一步的数据，使用 stage gate / hook / final quality hook 控制质量。

## 子 Skill

- `data_preparation`：数据获取、清洗、结构化整理。
- `news_analysis`：基于结构化事件做洞察分析。
- `report_generation`：生成 Markdown 报告、HTML 图表和最终质量检查结果。

## 输出

必须返回：

- `report`：Markdown 报告路径。
- `report_html`：完整 HTML 报告路径。
- `chart_html`：HTML 可视化路径。
- `pipeline_summary`：完整流程摘要路径。
- `run_id`：本次运行 ID。
- `quality_passed`：最终质量 hook 是否通过。
