# AGENTS.md

这个文件是给 Codex / Claude Code / Cursor 等 AI 编程助手看的项目级常驻上下文。它约束“怎么改这个仓库”，不是日报运行时给新闻分析模型看的业务 prompt。

## 两层 Harness 边界

本项目同时包含两层 Harness：

1. Coding Agent Harness：约束 Codex / Claude Code / Cursor 这类 AI 编程助手如何理解、修改、验证这个仓库。对应文件包括 `AGENTS.md`、`feature_list.json`、`progress.json`、`scripts/harness_linter.py`、`tests/` 和 `.github/workflows/harness.yml`。
2. Runtime Agent Harness：约束 Daily AI Insight Engine 运行时如何分阶段处理新闻、调用 LLM、使用工具、重试、校验和留痕。对应模块包括 `state.py`、`graph.py`、`stage_gates.py`、`hooks/`、`context_router.py`、`tool_gateway.py`、`prompt_builder.py` 和 `run_artifact`。

不要把这两层混成一个概念。`AGENTS.md` 是给 AI 编程助手看的项目级规则；`state.py`、`graph.py`、hook、linter、tool gateway、trace 和 run artifact 是约束本项目运行时 Agent 的控制层。

## 项目目标

Daily AI Insight Engine：从每日新闻信息中提取结构化洞察，生成可读的 Markdown 分析报告和 HTML 可视化结果。

当前架构目标不是做一个复杂平台，而是沉淀一个可学习、可追踪、可校验的 Harness 工程。

## 当前运行模式

```text
页面聊天
-> conversation router 判断用户意图
-> 普通问题：正常回复
-> 生成今日新闻分析报告：调用 daily_news_report_skill
-> daily_news_report_skill 启动 graph
-> graph 使用 state 跑完整流程
-> stage gate / hook / final quality hook 控制每一步
-> 返回 report、chart_html、pipeline_summary 给页面
```

## 项目文件纲要

```text
insight_engine/
├── AGENTS.md                              # AI 编程助手的项目常驻上下文和文件纲要
├── .env.example                           # DeepSeek 等环境变量示例
├── AI应用笔试题.md                         # 原始项目需求文档
├── feature_list.json                      # 功能完成标准和当前状态
├── progress.json                          # 跨会话学习进度和下一步计划
├── run_chat.py                            # 页面聊天的最小命令行入口
├── run_full_pipeline.py                   # 直接运行完整 daily_news_report_skill 的 smoke 入口
│
├── docs/
│   ├── runtime/
│   │   ├── workflow.md                    # 人看的流程说明，graph.py 才是执行真源
│   │   ├── global_rules.md                # 所有 LLM stage 共用的短规则
│   │   └── final_output_format.md         # 最终报告和结构化输出格式
│   └── rubrics/
│       └── quality_rubric.md              # final quality hook 参考的质量标准
│
├── prompts/
│   └── agents/
│       ├── structuring_agent.md           # 结构化 stage 的角色说明
│       ├── analysis_agent.md              # 分析 stage 的角色说明
│       ├── report_agent.md                # 报告生成 stage 的角色说明
│       └── reviewer_agent.md              # 最终质量检查 stage 的角色说明
│
├── skills/
│   ├── daily_news_report/
│   │   └── SKILL.md                       # 对话 Agent 可调用的完整日报能力说明
│   ├── data_preparation/
│   │   └── SKILL.md                       # 数据获取、清洗、结构化整理的能力说明
│   ├── news_analysis/
│   │   └── SKILL.md                       # 洞察分析和受限 ReAct 动作说明
│   └── report_generation/
│       └── SKILL.md                       # 报告、图表、最终质量 hook 的能力说明
│
├── scripts/
│   └── harness_linter.py                  # 静态 Harness 约束检查，适合放进 CI
│
├── src/
│   └── insight_engine/
│       ├── conversation/
│       │   └── router.py                  # 对话意图判断，决定是否调用日报 Skill
│       ├── skill_executors/
│       │   └── daily_news_report.py       # 可执行日报 Skill，内部启动 graph 并写 summary
│       ├── harness/
│       │   ├── state.py                   # 一次运行的共享状态和全部中间数据
│       │   ├── graph.py                   # 流程路由，决定下一步 stage 和重试位置
│       │   ├── stage_gates.py             # 每个 stage 结束后的产物规则检查
│       │   ├── stage_runner.py            # 单 stage 调试运行辅助
│       │   ├── context_router.py          # 控制每个 stage 能看到哪些 state 和文档
│       │   ├── skill_loader.py            # 把 Skill 文档加载进需要 LLM 的 stage
│       │   ├── prompt_builder.py          # 生成 prompt 快照，便于审计和复现
│       │   ├── tool_gateway.py            # 工具调用入口和白名单控制
│       │   ├── llm_client.py              # OpenAI-compatible / DeepSeek 调用封装
│       │   └── hooks/
│       │       ├── stage_hooks.py         # stage 前后快照和 trace 记录
│       │       ├── after_llm_call.py      # LLM 输出解析和基础结构检查
│       │       └── final_quality_hook.py  # 最终报告质量检查和回退建议
│       ├── stages/
│       │   ├── collect_raw_items.py       # 抓取 global 与 AI 两条数据线
│       │   ├── clean_items.py             # 清洗、去重、打标签、保留非 AI 信息
│       │   ├── structure_events.py        # LLM 或 fallback 生成结构化事件
│       │   ├── analyze_insights.py        # 受限 ReAct 分析热点、趋势、风险机会
│       │   └── generate_report.py         # 受限 ReAct 生成报告、图表和 manifest
│       ├── agents/
│       │   └── review_agent.py            # 触发 final quality hook 并写 review_result
│       └── tools/
│           └── quality_check.py           # final quality hook 使用的本地质量规则
│
├── tests/
│   ├── conftest.py                        # 测试路径配置
│   ├── test_graph.py                      # graph 路由和最小闭环测试
│   ├── test_harness_controls.py           # hook / tool gateway 基础测试
│   └── test_conversation_router.py        # 对话意图路由测试
│
├── data/
│   ├── raw/{run_id}/                      # 原始抓取数据
│   ├── processed/{run_id}/                # 清洗、结构化、分析结果
│   ├── prompts/{run_id}/                  # prompt 快照
│   ├── state/{run_id}/                    # state 快照
│   ├── react/{run_id}/                    # ReAct 每步响应
│   └── llm/{run_id}/                      # LLM 原始响应
│
└── outputs/
    ├── reports/{run_id}/                  # Markdown 报告和最终质量 hook
    ├── charts/{run_id}/                   # HTML 图表和 chart_data
    └── pipeline/{run_id}/                 # 完整流程摘要
```

## 分层规则

1. 页面或 CLI 只进入 `conversation/router.py` 或 `run_full_pipeline.py`。
2. 对话层只判断意图，不直接操作 state、graph、stage。
3. `daily_news_report_skill` 是业务能力入口，负责启动 graph 和整理返回结果。
4. `graph.py` 只管流程路由和重试，不写业务抓取、清洗、分析逻辑。
5. `state.py` 只管数据，不决定流程。
6. `stage_gates.py` 是每个 stage 的机械化检查，不写业务执行逻辑。
7. `hook` 用来记录、审计、触发质量检查；具体检查规则可以放到工具或 linter 函数里。

## Stage 规则

1. `collect_raw_items` 是确定性数据抓取 stage，不允许调用 LLM。
2. `clean_items` 是确定性清洗 stage，不允许调用 LLM。
3. `structure_events` 可以调用 LLM，但必须保留 prompt、LLM 响应、schema 校验和 fallback。
4. `analyze_insights` 可以使用受限 ReAct loop，但 action 必须白名单化。
5. `generate_report` 可以使用受限 ReAct loop，但必须输出 Markdown、chart_data、charts.html、manifest。
6. `review_and_eval` 只触发 final quality hook，不再引入独立 eval 概念。

## 产物规则

每次完整运行必须尽量保留以下链路：

```text
raw_items -> cleaned_items -> structured_events -> analysis_result -> report/chart -> final_quality_hook -> pipeline_summary
```

中间产物目录：

```text
data/raw/{run_id}/
data/processed/{run_id}/
data/prompts/{run_id}/
data/state/{run_id}/
data/react/{run_id}/
outputs/reports/{run_id}/
outputs/charts/{run_id}/
outputs/pipeline/{run_id}/
```

## 修改约束

1. 修改目录结构时，必须同步更新本文件的项目文件纲要。
2. 新增 stage 时，必须同步更新 `state.py`、`graph.py`、`stage_gates.py`、测试和 pipeline summary。
3. 新增 LLM stage 时，必须说明使用哪个 prompt、哪个 skill、如何校验输出、失败后如何 fallback。
4. 新增工具时，必须经过 `tool_gateway.py` 或明确说明为什么不经过 gateway。
5. 不允许静默删除非 AI 信息；应保留并打标签，便于追踪。
6. 修改确定性 stage 后，必须运行 `py -3 scripts/harness_linter.py`。
7. 修改完整流程后，必须运行 `py -3 run_chat.py "帮我生成今日新闻分析报告"` 或 `py -3 run_full_pipeline.py --show`。

## 学习顺序

当前推荐学习路线：

```text
State -> Graph -> Stage Gate/Linter -> Hook -> Prompt Builder -> Skill Loader -> Skill Executor -> Conversation Router -> ReAct Stage -> CI

```

## 执行

当前推荐学习路线：

```text
py -3 run_chat.py "帮我生成今日新闻分析报告"

```
