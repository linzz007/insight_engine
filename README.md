# Daily AI Insight Engine

Daily AI Insight Engine 是一个学习型 Harness 工程：从每日新闻源抓取信息，经过清洗、结构化、洞察分析、报告生成和最终质量检查，输出 Markdown 报告、HTML 报告、HTML 图表和完整运行摘要。

这个项目的重点不是做复杂平台，而是把一个多阶段 AI 工作流做成可学习、可追踪、可校验的工程样板。

## Harness 边界

本项目有两层 Harness，不能混在一起理解：

- Coding Agent Harness：约束 Codex / Claude Code / Cursor 这类 AI 编程助手如何修改仓库。核心文件是 `AGENTS.md`、`feature_list.json`、`progress.json`、`scripts/harness_linter.py`、`tests/` 和 `.github/workflows/harness.yml`。
- Runtime Agent Harness：约束日报运行时 Agent 如何分阶段处理数据、调用 LLM、使用工具、重试、校验和留痕。核心模块是 `state.py`、`graph.py`、`stage_gates.py`、`hooks/`、`context_router.py`、`tool_gateway.py`、`prompt_builder.py` 和 `run_artifact`。

`AGENTS.md` 是给 AI 编程助手看的项目规则；`state.py`、`graph.py`、hook、stage gate、tool gateway、trace 和 run artifact 才是日报运行时的控制层。

## 运行流程

```text
页面聊天 / CLI
-> conversation.router 判断用户意图
-> 普通问题：返回普通说明
-> 日报请求：调用 daily_news_report_skill
-> daily_news_report_skill 创建 graph
-> graph 按 state 执行 stage
-> stage gate / hook / final quality hook 控制每一步
-> 输出 report、report_html、chart_html、pipeline_summary、run_artifact
```

完整数据链路：

```text
raw_items
-> cleaned_items
-> structured_events
-> analysis_result
-> report / chart
-> final_quality_hook
-> pipeline_summary / run_artifact
```

## 目录结构

```text
insight_engine/
├── AGENTS.md
├── README.md
├── .env.example
├── AI应用笔试题.md
├── feature_list.json
├── progress.json
├── run_chat.py
├── run_full_pipeline.py
├── config/sources.json
├── docs/
│   ├── runtime/global_rules.md
│   ├── runtime/final_output_format.md
│   └── rubrics/quality_rubric.md
├── prompts/agents/
├── skills/
├── scripts/harness_linter.py
├── src/insight_engine/
│   ├── conversation/
│   ├── skill_executors/
│   ├── harness/
│   ├── stages/
│   ├── agents/
│   ├── linters/
│   └── tools/
└── tests/
```

运行时会生成以下忽略目录：

```text
data/raw/{run_id}/
data/processed/{run_id}/
data/prompts/{run_id}/
data/state/{run_id}/
data/react/{run_id}/
data/llm/{run_id}/
outputs/reports/{run_id}/
outputs/charts/{run_id}/
outputs/pipeline/{run_id}/
```

这些目录是可再生成的运行产物，不是源码。

## 快速开始

使用 Windows PowerShell：

```powershell
py -3 run_chat.py "你好"
py -3 run_chat.py "帮我生成今日新闻分析报告" --show
py -3 run_full_pipeline.py --show
```

完整日报流程建议先复制 `.env.example` 为 `.env`，并填写 `DEEPSEEK_API_KEY`。当前 `structure_events`、`analyze_insights` 和 Stage 5 标题翻译都可能使用 DeepSeek；如果没有 key 或 LLM 失败，部分 stage 会 fallback，但完整 gate 不一定通过。

## 验证命令

```powershell
py -3 -m compileall src scripts tests
py -3 scripts/harness_linter.py
py -3 -m pytest
```

如果本机没有 `pytest`，先安装测试工具：

```powershell
py -3 -m pip install pytest
```

CI 会在 Windows 上运行 compileall、harness linter 和 pytest。

## 关键模块

- `src/insight_engine/conversation/router.py`：对话意图分流，只决定是否触发日报 Skill。
- `src/insight_engine/skill_executors/daily_news_report.py`：日报业务能力入口，负责启动 graph 并整理返回结果。
- `src/insight_engine/harness/state.py`：一次运行的共享状态和跨阶段字段合同。
- `src/insight_engine/harness/graph.py`：流程路由和重试控制。
- `src/insight_engine/harness/stage_gates.py`：stage 结束后的机械化检查调度。
- `src/insight_engine/harness/hooks/`：prompt 快照、state 快照、trace 和最终质量检查。
- `src/insight_engine/harness/context_router.py`：决定每个 stage 能看到哪些 state 字段和 runtime docs。
- `src/insight_engine/harness/tool_gateway.py`：运行时工具白名单入口。
- `src/insight_engine/stages/`：抓取、清洗、结构化、分析和报告生成的真实业务逻辑。
- `src/insight_engine/linters/`：每个 stage 的产物合同检查。

## Docs 使用情况

`docs/` 不是闲置文档，它们会进入运行时 prompt 或最终质量检查语境：

- `docs/runtime/global_rules.md`：注入 `structure_events`、`analyze_insights`、`generate_report` 和 `review_and_eval`。
- `docs/runtime/final_output_format.md`：注入上述 LLM / review stage，用于约束最终报告和结构化输出。
- `docs/rubrics/quality_rubric.md`：注入 `review_and_eval`，作为 final quality hook 的质量参考。

这些引用由 `src/insight_engine/harness/context_router.py` 的 `RUNTIME_DOCS` 维护。

## 清理原则

- 不删除 `docs/`、`prompts/`、`skills/` 中被 prompt 构建或 linter 合同引用的文件。
- 不静默删除非 AI 新闻或原始数据，清洗阶段只打标签并保留追踪信息。
- `data/`、`outputs/`、`__pycache__/`、`.pytest_cache/` 是运行产物或缓存，已在 `.gitignore` 中忽略。
- 新增 stage 时必须同步更新 `state.py`、`graph.py`、`stage_gates.py`、测试和 pipeline summary。
