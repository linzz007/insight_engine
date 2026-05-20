# report_generation

## 目标

把分析结果生成可读报告、可视化图表和最终质量检查产物。

## 范围

覆盖两个 stage：

- `generate_report`：先用 LLM 把英文标题忠实翻译成中文，再用确定性模板生成 Markdown 报告、暗色中文 HTML 看板、左侧侧边导航、饼状图、chart_data、charts.html、manifest。
- `review_and_eval`：触发 final quality hook，写出最终质量检查结果。

## 报告必须包含

- 数据源概览
- 全球热点背景
- 今日 AI 领域主要热点
- 重要事件深度总结
- 趋势判断
- 风险和机会提示
- 结构化数据附录
- 质量评估摘要

## 约束

- 报告不得丢失事件 id 和来源 URL。
- 图表数据必须来自 `analysis_result` 或 structured events，不允许凭空编造。
- HTML 报告必须以中文为主，首屏展示一句话结论、KPI 和饼状图。
- HTML 报告必须使用左侧侧边导航 + 右侧纵向内容流，不再把正文分成左右两栏。
- 事件卡片必须把英文标题原封不动翻译成中文放在最前，英文原题、关键词、摘要、理由和来源链接在下方。
- 如果 `DEEPSEEK_API_KEY` 未配置或标题翻译失败，不能用规则拼接标题冒充翻译；必须保留英文原题并写入 warning，严格 linter 应判定标题翻译未达标。
- `chart_data` 必须包含 `kpis`、`pies`、`top_ai_events`、`global_context_events`、`trend_cards` 和 `risk_opportunity_matrix`，让页面组件直接消费。
- final quality hook 失败时，graph 决定是否回退到指定 stage 重跑。
- 最终必须写出 `daily_ai_report.md`、`daily_ai_report.html`、`charts.html`、`chart_data.json` 和 `final_quality_hook.json`。
