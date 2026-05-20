# data_preparation

## 目标

把外部数据源变成可分析的结构化事件，同时保留可追踪证据。

## 范围

覆盖三个 stage：

- `collect_raw_items`：从外部 API/RSS/聚合源抓取 global 与 AI 两条数据线。
- `clean_items`：去重、标准化字段、补充标签和质量分。
- `structure_events`：把 cleaned item 转成 structured event。

## 约束

- 抓取和清洗阶段不调用 LLM。
- 不删除非 AI 信息，global 数据线保留广泛热点，clean 阶段打标签。
- AI 数据线可以基于关键词和来源做筛选，但必须记录命中的关键词和来源。
- 结构化阶段可以调用 LLM，但必须保留 prompt、LLM 响应、schema linter 结果和 fallback。
- 每个结构化事件必须能追溯到 `raw_ref` 和 `evidence.source_url`。

## 输出字段

核心输出是：

- `global_raw_items`
- `ai_raw_items`
- `global_cleaned_items`
- `ai_cleaned_items`
- `global_structured_events`
- `ai_structured_events`

