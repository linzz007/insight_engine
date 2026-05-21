# AI舆情分析日报系统（Daily AI Insight Engine）

> 从每日新闻信息中提取结构化洞察，并生成可读的分析报告与可视化结果

## 5.21报告
daily_ai_report.html
## 一、数据源说明

### 1.1 数据源选择

系统通过 RSS 和 API 从多个公开新闻源抓取数据，分为两条数据线：

#### Global 数据线（全球热点背景）

| 数据源 | 类型 | 接入方式 | 说明 |
|---|---|---|---|
| NPR Top News | 媒体 | RSS | 美国公共广播新闻，覆盖政治、经济、科技等广泛领域 |
| Google News Top | 聚合平台 | RSS | Google 新闻头条，反映美国主流媒体议程 |

#### AI 数据线（AI 专业领域）

| 数据源 | 类型 | 接入方式 | 说明 |
|---|---|---|---|
| TechCrunch AI | 科技媒体 | RSS | 专注 AI/创业报道，更新频率高，一手信息多 |
| The Verge AI | 科技媒体 | RSS | AI 板块独立 RSS，内容质量较高 |
| Hacker News AI | 技术社区 | API（Algolia） | 技术社区对 AI 话题的讨论热度，附带 points/comments 社会信号 |

另有 arXiv（学术论文）、Reddit r/artificial（社交讨论）等备用数据源，当前因网络限制或需 API 认证暂未启用。

### 1.2 数据源选择理由

- **中英文混合**：TechCrunch、The Verge 为英文源，Hacker News 为英文技术社区，覆盖国际 AI 资讯；NPR、Google News 以英文为主，提供美国舆情背景。
- **类型互补**：媒体源（NPR、TechCrunch、The Verge）提供经过编辑审核的报道；聚合平台（Google News）反映大众关注度；技术社区（Hacker News）反映开发者群体对 AI 的真实讨论热度。
- **信号多元**：Hacker News 提供 points（点赞数）和 num_comments（评论数），可作为热度判断的社会信号补充。

### 1.3 数据特点

- 每条原始数据包含：标题、正文/摘要、来源、发布时间、URL
- 抓取时自动过滤 2 天前的旧数据（`max_age_days: 2`）
- 每个数据源有独立的 `min_items` 阈值和 `max_attempts` 重试次数
- AI 数据源配置了关键词过滤（约 25 个 AI 相关关键词），减少无关数据
- 数据抓取失败时自动重试，全部失败则记录 warning 但不阻塞流程

---

## 二、系统设计思路

### 2.1 整体架构

系统采用 **多阶段流水线（Pipeline）+ Harness 工程** 架构，核心设计理念是将 AI 工作流工程化：

```text
                   ┌─────────────┐
  用户输入 ──────→ │ Conversation│ ── 普通消息 ──→ 直接回复
  (聊天/CLI)       │   Router    │
                   │ (意图分流)   │ ── 日报请求 ──→ Skill Executor
                   └─────────────┘                      │
                                           ┌────────────┘
                                           ▼
                              ┌──────────────────────┐
                              │   Insight Engine     │
                              │   Graph (状态机)      │
                              │                      │
                              │  Stage 1: 数据抓取    │
                              │     ↓                │
                              │  Stage 2: 数据清洗    │
                              │     ↓                │
                              │  Stage 3: 结构化抽取  │ ← LLM
                              │     ↓                │
                              │  Stage 4: 洞察分析    │ ← ReAct LLM
                              │     ↓                │
                              │  Stage 5: 报告生成    │ ← ReAct LLM
                              │                      │
                              │  每个 Stage 后：       │
                              │  Hook → Linter → Gate│
                              └──────────────────────┘
                                      │
                                      ▼
                              输出：Report(.md/.html)
                                    Chart(.html)
                                    Pipeline Summary
                                    Run Artifact
```

### 2.2 关键设计决策

#### 决策 1：两层 Harness 分离

项目包含两层 Harness，严格分离：

- **Coding Agent Harness**：约束 AI 编程助手如何修改仓库（AGENTS.md、feature_list.json、CI、harness_linter.py）
- **Runtime Agent Harness**：约束日报运行时 Agent 如何分阶段处理数据（state.py、graph.py、stage_gates.py、hooks/、tool_gateway.py）

两层不混用，各自有独立的规则、检查机制和可审计产物。

#### 决策 2：Stage Gate + Hook 插槽系统

每个 stage 结束后不依赖 LLM 自评，而是用**确定性代码**检查产物是否满足最低要求（Linter）。Linter 通过 StageHooks 插槽系统挂载，graph 不直接感知 linter 的存在——只看到 hook 返回值。

```
fire_before → handler() → fire_after
                              │
              ┌─ linter 通过 ─→ 进入下一 stage
              │
              └─ linter 失败 ─→ 重试或终止
```

关键特性：
- 每个 stage 的 linter 独立定义阈值（如 `HARNESS_MIN_GLOBAL_RAW=5`），可通过环境变量调整
- 重试由 `HARNESS_STAGE_MAX_RETRY`（默认 1 次）控制
- 重试仍不通过时记录 error 并终止流程

#### 决策 3：全局 + AI 双数据线

系统同时维护两条数据线，不删除非 AI 信息：

- **Global 线**：保留广泛热点，用于判断今日公共舆情背景
- **AI 线**：聚焦 AI 专业领域，用于深度洞察

清洗阶段只打标签（`is_ai_related`、`should_analyze_ai`），不删除数据，保留追踪信息。

#### 决策 4：确定性阶段与 LLM 阶段分层

| Stage | 类型 | 说明 |
|---|---|---|
| collect_raw_items | 确定性（无 LLM） | 纯 RSS/API 抓取，不调用模型 |
| clean_items | 确定性（无 LLM） | 纯规则清洗、去重、打标签 |
| structure_events | LLM + Schema Linter + Fallback | 批量输入 → LLM JSON → 本地校验 → repair/兜底 |
| analyze_insights | 受限 ReAct + Fallback | 固定计划、白名单 action、本地函数执行 |
| generate_report | 受限 ReAct + Fallback | 固定计划、白名单 action、输出报告+图表 |

**关键原则**：能确定性完成的不调用 LLM；LLM 不可用时必须有 rule-based fallback，系统不能崩溃。

#### 决策 5：Schema 驱动的数据合同

结构化事件的字段规范定义在 `state.py` 的 `STRUCTURED_EVENT_FIELD_SPEC` 中，LLM 输出必须满足此合同。Schema linter 不依赖 LLM 自评，而是用确定性代码逐字段检查。

#### 决策 6：全链路可审计

每个 stage 都会自动保存产物：
- `data/raw/{run_id}/` — 原始抓取数据
- `data/processed/{run_id}/` — 清洗、结构化、分析结果
- `data/prompts/{run_id}/` — 每个 LLM stage 的完整 prompt 快照
- `data/llm/{run_id}/` — LLM 原始响应（含 initial_response 和 repair_response）
- `data/react/{run_id}/` — ReAct 每步的 prompt/响应
- `data/state/{run_id}/` — 每个 stage 后的完整 state 快照
- `outputs/pipeline/{run_id}/` — 流程摘要、stage trace、stage gate 结果

---

## 三、AI 使用方式

### 3.1 使用场景

系统中 LLM（DeepSeek）仅在以下 stage 中使用：

| Stage | LLM 用途 | 调用模式 |
|---|---|---|
| structure_events | 将清洗后的新闻转成结构化事件 JSON | 单次 Chat Completions + repair |
| analyze_insights | 识别热点、Top 事件、趋势信号 | 受限 ReAct loop（5 步固定计划） |
| generate_report | 生成 Markdown 报告、图表数据和 HTML | 受限 ReAct loop（5 步固定计划） |

LLM 不做的事：
- 不负责数据抓取（Stage 1 确定）
- 不负责数据清洗（Stage 2 确定）
- 不负责校验自己的输出（由本地 linter 检查）
- 不调用外部工具（所有 action 由本地函数执行）

### 3.2 Prompt 设计

每个 LLM stage 的 prompt 遵循**结构化注入**模式，由 `prompt_builder.py` 统一构造：

```
System Prompt（角色定义 + 硬约束）
  +
Task Prompt（任务描述 + 输出格式 + Schema 合同）
  +
Context（来自 state 的字段子集，由 context_router 控制）
  +
Retry Feedback（上次 linter 失败的具体原因）
```

约束策略：
- **角色约束**：`prompts/agents/` 下的 agent prompt 定义角色边界
- **规则约束**：`docs/runtime/global_rules.md` 注入全局行为规则
- **格式约束**：`docs/runtime/final_output_format.md` 注入输出格式要求
- **Schema 约束**：prompt 中包含完整的字段合同（required fields、allowed values）
- **质量约束**：`docs/rubrics/quality_rubric.md` 用于 final quality check

### 3.3 错误处理

系统设计为 **渐进降级（Graceful Degradation）**，而非硬失败：

```
优先级 1：LLM 正常输出
    ↓ 失败
优先级 2：LLM repair（把 linter 错误反馈给 LLM，要求修复）
    ↓ 仍失败
优先级 3：Rule-based fallback（确定性规则生成结果，标注 fallback 来源）
    ↓ 确保系统始终可运行
```

具体策略：
- **LLM 超时/不可用**：自动降级到规则 fallback，记录 warning
- **JSON 解析失败**：`after_llm_call.parse_json_output` 尝试从文本中提取 JSON
- **Schema linter 不通过**：触发一次 repair，仍不通过则 fallback
- **ReAct 动作违规**：linter 拦截非预期动作，记录 observation，强制 LLM 按计划执行
- **ReAct 超步数**：超过 `ANALYZE_REACT_MAX_STEPS` 后自动 fallback

所有错误和降级都记录在 `state.warnings` / `state.errors` 中，最终出现在 `pipeline_summary` 里，方便排查。

---

## 四、核心流程说明

### 4.1 完整数据链路

```text
原始数据 (raw_items)
    │  从 NPR、Google News、TechCrunch、The Verge、Hacker News 抓取
    │  global + AI 两条线，每条线独立抓取和计数
    ▼
清洗数据 (cleaned_items)
    │  去重、标准化字段、打标签（is_ai_related、should_analyze_ai 等）
    │  不删除非 AI 信息，保留追踪引用 raw_ref
    ▼
结构化事件 (structured_events)
    │  LLM 将 cleaned items 转成统一 Schema 的结构化事件
    │  包含：行业方向、热度分、重要性、影响分析、风险/机会判断
    │  LLM 失败时规则 fallback，保证系统继续运行
    ▼
分析结果 (analysis_result)
    │  受限 ReAct：统计 → Top 选择 → 趋势聚合 → finish
    │  输出：整体判断、AI Top 5、global Top 5、四维趋势、风险机会
    ▼
最终报告 (report + chart)
    │  ReAct 生成：Markdown 报告 + 图表数据 + HTML 可视化
    │  包含：头部概览、Top 事件卡片、趋势仪表盘、风险机会面板
```

### 4.2 各阶段详细说明

#### Stage 1: collect_raw_items（数据抓取）

- 读取 `config/sources.json` 中已启用的数据源配置
- 对每个数据源按 `max_attempts` 重试抓取
- 按 `max_age_days` 过滤过旧数据
- 对 AI 数据源按关键词过滤
- 写入 `data/raw/{run_id}/raw_items.json`
- **无 LLM 调用**

#### Stage 2: clean_items（数据清洗）

- 标准化字段名、统一日期格式
- 基于关键词匹配判断是否 AI 相关（`is_ai_related`）
- 基于质量评分决定是否进入分析（`should_analyze_ai`、`should_analyze_global`）
- 去重：URL 完全相同或标题相似度 >= 85% 的视为重复
- 写入 `data/processed/{run_id}/cleaned_items.json`
- **无 LLM 调用**

#### Stage 3: structure_events（结构化抽取）

- 将 `cleaned_items` 转为统一 Schema 的 `structured_events`
- 调用 DeepSeek 做批量抽取（JSON 输入 → JSON 输出）
- 本地 schema linter 检查：必填字段、引用一致性、值范围
- Linter 失败时，将具体错误反馈给 LLM 做一次 repair
- Repair 仍失败或 LLM 不可用时，使用规则 fallback
- 输出 `global_structured_events` 和 `ai_structured_events`
- **LLM 阶段，含 repair + fallback**

#### Stage 4: analyze_insights（洞察分析）

- 受限 ReAct loop，固定 5 步计划：

| 步骤 | 动作 | 目标 |
|---|---|---|
| Step 1 | inspect_event_stats | 统计事件分布（行业、来源、标签） |
| Step 2 | select_top_events (scope=ai) | 选择 AI Top 5 事件 |
| Step 3 | select_top_events (scope=global) | 选择全球背景 Top 5 事件 |
| Step 4 | build_trend_signals | 聚合技术/应用/政策/资本四维趋势 |
| Step 5 | finish | 输出完整 analysis_result |

- LLM 只负责选择 action，实际执行由本地确定性函数完成
- 每步的 prompt + 响应保存到 `data/react/{run_id}/analyze_insights/step_*.json`
- **LLM 阶段，含 ReAct trace + fallback**

#### Stage 5: generate_report（报告生成）

- 受限 ReAct loop，固定 5 步计划：

| 步骤 | 动作 | 目标 |
|---|---|---|
| Step 1 | prepare_data | 从分析结果中提取报告所需数据 |
| Step 2 | generate_report_md | 生成中文 Markdown 报告 |
| Step 3 | render_html | 将 Markdown 转为 HTML |
| Step 4 | generate_chart | 生成 ECharts 图表数据 |
| Step 5 | finish | 输出完整 report_manifest |

- 输出文件：
  - `outputs/reports/{run_id}/daily_ai_report.md` — Markdown 报告
  - `outputs/reports/{run_id}/daily_ai_report.html` — HTML 报告
  - `outputs/reports/{run_id}/title_translations.json` — 标题翻译
  - `outputs/charts/{run_id}/charts.html` — 可视化图表
  - `outputs/charts/{run_id}/chart_data.json` — 图表数据
  - `outputs/pipeline/{run_id}/pipeline_summary.md` — 流程摘要
- **LLM 阶段，含 ReAct trace + fallback**

### 4.3 关键数据结构

**Structured Event Schema**：每个结构化事件包含约 20 个字段，核心字段包括：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | 唯一标识，格式 `event_{scope}_{n}` |
| title | string | 事件标题 |
| source_name | string | 来源标识 |
| industry_area | enum | 行业方向（AI: foundation_model/ai_infra/policy/investment/research/ai_app/robotics/security/other；Global: politics/business/technology/health/education/environment/other） |
| hotness_score | int(0-100) | 热度评分 |
| importance_level | enum | 重要性等级（high/medium/low） |
| impact_analysis | string | 影响分析 |
| risk_or_opportunity | string | 风险或机会判断 |
| evidence | object | 证据链（source_title、source_url、supporting_text） |
| raw_ref | string | 回溯引用，指向原始 cleaned_item |

---

## 五、Harness 工程

本项目在实现 MVP 的同时，沉淀了一套 Harness Engineering 体系：

### 5.1 Coding Agent Harness

约束 AI 编程助手如何修改仓库：

- `AGENTS.md` — 项目级常驻上下文，定义文件纲要、分层规则、修改约束、学习顺序
- `feature_list.json` — 功能完成标准和当前状态（F001-F009）
- `progress.json` — 跨会话学习进度和下一步计划
- `scripts/harness_linter.py` — 静态 Harness 约束检查，CI 自动运行
- `.github/workflows/harness.yml` — CI 流水线（compileall + harness_linter + pytest）

### 5.2 Runtime Agent Harness

约束运行时 AI Agent 的行为：

- `state.py` — 一次运行的共享状态、字段合同、Schema 定义
- `graph.py` — Stage 状态机，路由 + 重试控制
- `stage_gates.py` — 每个 stage 的机械化产物检查调度
- `hooks/stage_hooks.py` — StageHooks 插槽系统（before/after 生命周期）
- `context_router.py` — 控制每个 stage 能看到哪些 state 字段和文档
- `tool_gateway.py` — 运行时工具白名单入口
- `prompt_builder.py` — Prompt 构造、快照保存、retry feedback
- `linters/` — 每个 stage 的产物合同检查（独立于 stage 执行逻辑）

### 5.3 Skills

- `skills/daily_news_report/SKILL.md` — 日报 Skill 定义，LLM 读取此文件判断是否触发日报流程
- 对话路由通过 `conversation/router.py` 判断用户意图，普通消息不触发完整流程

---

## 六、快速开始

### 环境准备

```powershell
# 复制环境变量配置，填写 DEEPSEEK_API_KEY
copy .env.example .env
```

### 运行命令

```powershell
# 对话入口（推荐）
py -3 run_chat.py "帮我生成今日新闻分析报告"

# 完整流水线（跳过对话路由）
py -3 run_full_pipeline.py --show

# 普通对话
py -3 run_chat.py "你好"
```

### 验证命令

```powershell
# 编译检查
py -3 -m compileall src scripts tests

# Harness 静态检查
py -3 scripts/harness_linter.py

# 单元测试
py -3 -m pytest
```

---

## 七、输出示例

最新生成的日报报告：[daily_ai_report.html](daily_ai_report.html)

每次运行会生成以下产物：

```
outputs/
├── reports/{run_id}/
│   ├── daily_ai_report.md          # Markdown 报告
│   ├── daily_ai_report.html        # HTML 报告（可直接浏览器打开）
│   └── title_translations.json     # 标题翻译
├── charts/{run_id}/
│   ├── charts.html                 # ECharts 可视化图表
│   └── chart_data.json             # 图表数据
└── pipeline/{run_id}/
    ├── pipeline_summary.md          # 流程摘要（含 stage trace、gate 结果、warnings）
    └── run_artifact.json            # 完整运行产物清单
```

---

## 八、目录结构

```text
insight_engine/
├── AGENTS.md                       # AI 编程助手的项目规则
├── README.md                       # 项目说明文档（本文件）
├── .env.example                    # 环境变量示例
├── AI应用笔试题.md                  # 原始项目需求文档
├── feature_list.json               # 功能完成标准
├── progress.json                   # 跨会话学习进度
├── run_chat.py                     # 对话入口
├── run_full_pipeline.py            # 完整流水线入口
├── config/sources.json             # 数据源配置
├── docs/
│   ├── runtime/                    # 运行时注入 prompt 的规则文档
│   └── rubrics/                    # 质量评估标准
├── prompts/agents/                 # Agent 角色 prompt
├── skills/daily_news_report/       # 日报 Skill 定义
├── scripts/harness_linter.py       # Harness 静态检查
├── src/insight_engine/
│   ├── conversation/               # 对话意图路由
│   ├── skill_executors/            # Skill 执行器
│   ├── harness/                    # Runtime Harness（state/graph/gate/hook/tool/prompt）
│   ├── stages/                     # 5 个 stage 的业务逻辑
│   ├── linters/                    # 每个 stage 的产物合同检查
│   ├── agents/                     # Agent stage 处理器
│   └── tools/                      # 运行时工具
└── tests/                          # 单元测试
```
