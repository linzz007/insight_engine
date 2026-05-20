# news_analysis

## 目标

基于结构化事件生成今日热点、趋势判断和风险机会提示。

## 范围

覆盖 `analyze_insights` stage。

## 分析规则

- AI 数据线用于专业洞察，global 数据线用于舆情和背景参照。
- 优先选择有明确来源、发布时间、影响分析和较高 hotness_score 的事件。
- 输出 AI Top 事件时必须保留事件 id、标题、URL、摘要和重要性说明。
- 输出 global Top 事件时必须保留事件 id、标题、URL、摘要和背景意义。
- 趋势判断至少覆盖技术、应用、政策、资本四类。
- 风险或机会提示必须绑定支持事件，不能凭空判断。
- 所有关键判断必须给出理由字段：整体判断使用 `summary_reason`，Top 事件使用 `selection_reason`，趋势判断使用 `trend_reasoning`，风险机会提示使用 `reason`。

## ReAct 约束

允许的动作只包括：

- `inspect_event_stats`
- `select_top_events`
- `build_trend_signals`
- `finish`

必须按固定顺序执行：

1. `inspect_event_stats`
2. `select_top_events`，参数为 `{"scope": "ai", "limit": 5}`
3. `select_top_events`，参数为 `{"scope": "global", "limit": 5}`
4. `build_trend_signals`
5. `finish`

`finish` 输出必须能直接供报告阶段使用，不能只给空泛结论。
后续轮次会看到完整 ReAct 上下文，包括历史 action payload、observation 和 linter feedback；必须基于这些上下文继续分析。

如果 LLM 不可用或输出不合格，使用本地规则 fallback，并保留 fallback trace。
