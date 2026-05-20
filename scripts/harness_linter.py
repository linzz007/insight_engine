"""Static Harness linter.

这个 linter 检查的是工程约束，不检查日报内容质量。它适合本地和 CI 执行：
    py -3 scripts/harness_linter.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "feature_list.json",
    "progress.json",
    "run_chat.py",
    "run_full_pipeline.py",
    ".github/workflows/harness.yml",
    "docs/runtime/global_rules.md",
    "docs/runtime/final_output_format.md",
    "docs/rubrics/quality_rubric.md",
    "src/insight_engine/conversation/router.py",
    "src/insight_engine/skill_executors/daily_news_report.py",
    "src/insight_engine/harness/state.py",
    "src/insight_engine/harness/graph.py",
    "src/insight_engine/harness/stage_gates.py",
    "src/insight_engine/harness/stage_runner.py",
    "src/insight_engine/harness/context_router.py",
    "src/insight_engine/harness/env.py",
    "src/insight_engine/harness/skill_loader.py",
    "src/insight_engine/harness/prompt_builder.py",
    "src/insight_engine/harness/tool_gateway.py",
    "src/insight_engine/harness/llm_client.py",
    "src/insight_engine/harness/hooks/stage_hooks.py",
    "src/insight_engine/harness/hooks/after_llm_call.py",
    "src/insight_engine/harness/hooks/final_quality_hook.py",
]

SKILL_FILES = [
    "skills/daily_news_report/SKILL.md",
    "skills/data_preparation/SKILL.md",
    "skills/news_analysis/SKILL.md",
    "skills/report_generation/SKILL.md",
]

PROMPT_FILES = [
    "prompts/agents/structuring_agent.md",
    "prompts/agents/analysis_agent.md",
    "prompts/agents/report_agent.md",
    "prompts/agents/reviewer_agent.md",
]

STAGE_LINTER_PAIRS = {
    "collect_raw_items": (
        "src/insight_engine/stages/collect_raw_items.py",
        "src/insight_engine/linters/collect_raw_items.py",
    ),
    "clean_items": (
        "src/insight_engine/stages/clean_items.py",
        "src/insight_engine/linters/clean_items.py",
    ),
    "structure_events": (
        "src/insight_engine/stages/structure_events.py",
        "src/insight_engine/linters/structure_events.py",
    ),
    "analyze_insights": (
        "src/insight_engine/stages/analyze_insights.py",
        "src/insight_engine/linters/analyze_insights.py",
    ),
    "generate_report": (
        "src/insight_engine/stages/generate_report.py",
        "src/insight_engine/linters/generate_report.py",
    ),
    "review_and_eval": (
        "src/insight_engine/agents/review_agent.py",
        "src/insight_engine/linters/review_and_eval.py",
    ),
}

DETERMINISTIC_STAGE_FILES = [
    "src/insight_engine/stages/collect_raw_items.py",
    "src/insight_engine/stages/clean_items.py",
]

FORBIDDEN_LLM_TOKENS = [
    "OpenAICompatibleChatClient",
    "chat_json(",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
]

AGENTS_REQUIRED_PHRASES = [
    "Coding Agent Harness",
    "Runtime Agent Harness",
    "Codex / Claude Code / Cursor",
    "state.py",
    "graph.py",
    "tool_gateway.py",
    "run_artifact",
    "py -3 scripts/harness_linter.py",
]

JSON_CONTRACTS = {
    "feature_list.json": ["project", "purpose", "features"],
    "progress.json": [
        "project",
        "current_learning_goal",
        "last_updated",
        "completed",
        "active_harness_concepts",
        "next_steps",
    ],
}


def main() -> int:
    issues: list[str] = []
    issues.extend(check_required_files())
    issues.extend(check_no_confusing_agent_file())
    issues.extend(check_agents_contract())
    issues.extend(check_json_contracts())
    issues.extend(check_deterministic_stages_do_not_call_llm())
    issues.extend(check_skills_and_prompts())
    issues.extend(check_stage_linter_pairs())
    issues.extend(check_full_pipeline_has_show_flag())
    issues.extend(check_chat_entrypoint())
    issues.extend(check_ci_workflow())

    payload = {
        "passed": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


def check_required_files() -> list[str]:
    issues = []
    for relative_path in REQUIRED_FILES:
        if not (PROJECT_ROOT / relative_path).exists():
            issues.append(f"缺少必需文件：{relative_path}")
    return issues


def check_no_confusing_agent_file() -> list[str]:
    issues = []
    for filename in ["agent.md", "AGENT.md", "Agent.md"]:
        if (PROJECT_ROOT / filename).exists():
            issues.append(
                f"根目录不应维护 {filename}；AI 编程助手入口统一使用 AGENTS.md，人类说明使用 README.md"
            )
    return issues


def check_agents_contract() -> list[str]:
    path = PROJECT_ROOT / "AGENTS.md"
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    issues = []
    for phrase in AGENTS_REQUIRED_PHRASES:
        if phrase not in text:
            issues.append(f"AGENTS.md 缺少项目级 Harness 关键词：{phrase}")
    return issues


def check_json_contracts() -> list[str]:
    issues = []
    for relative_path, required_keys in JSON_CONTRACTS.items():
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"{relative_path} 不是合法 JSON：{exc}")
            continue

        if not isinstance(data, dict):
            issues.append(f"{relative_path} 顶层必须是 JSON object")
            continue

        for key in required_keys:
            if key not in data:
                issues.append(f"{relative_path} 缺少字段：{key}")

        issues.extend(_check_non_empty_list(data, relative_path, "feature_list.json", "features"))
        issues.extend(_check_non_empty_list(data, relative_path, "progress.json", "completed"))
        issues.extend(_check_non_empty_list(data, relative_path, "progress.json", "active_harness_concepts"))
        issues.extend(_check_non_empty_list(data, relative_path, "progress.json", "next_steps"))

    return issues


def _check_non_empty_list(
    data: dict[str, Any],
    relative_path: str,
    target_file: str,
    key: str,
) -> list[str]:
    if relative_path != target_file or key not in data:
        return []
    if not isinstance(data[key], list) or not data[key]:
        return [f"{relative_path}.{key} 必须是非空数组"]
    return []


def check_deterministic_stages_do_not_call_llm() -> list[str]:
    issues = []
    for relative_path in DETERMINISTIC_STAGE_FILES:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            issues.append(f"确定性 stage 文件不存在：{relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_LLM_TOKENS:
            if token in text:
                issues.append(f"{relative_path} 不应直接调用 LLM 或读取模型配置：{token}")
    return issues


def check_skills_and_prompts() -> list[str]:
    issues = []
    for relative_path in [*SKILL_FILES, *PROMPT_FILES]:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            issues.append(f"缺少 prompt/skill 文件：{relative_path}")
        elif not path.read_text(encoding="utf-8").strip():
            issues.append(f"prompt/skill 文件为空：{relative_path}")
    return issues


def check_stage_linter_pairs() -> list[str]:
    issues = []
    for stage_name, (stage_path, linter_path) in STAGE_LINTER_PAIRS.items():
        if not (PROJECT_ROOT / stage_path).exists():
            issues.append(f"{stage_name} 缺少 stage/agent 实现文件：{stage_path}")
        if not (PROJECT_ROOT / linter_path).exists():
            issues.append(f"{stage_name} 缺少对应 linter：{linter_path}")
    return issues


def check_full_pipeline_has_show_flag() -> list[str]:
    path = PROJECT_ROOT / "run_full_pipeline.py"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if "--show" not in text:
        return ["run_full_pipeline.py 必须支持 --show，方便查看完整流程摘要"]
    return []


def check_chat_entrypoint() -> list[str]:
    path = PROJECT_ROOT / "run_chat.py"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if "handle_message" not in text:
        return ["run_chat.py 必须通过 conversation.router.handle_message 进入系统"]
    return []


def check_ci_workflow() -> list[str]:
    path = PROJECT_ROOT / ".github/workflows/harness.yml"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    required_tokens = [
        "compileall",
        "scripts/harness_linter.py",
        "pytest",
    ]
    issues = []
    for token in required_tokens:
        if token not in text:
            issues.append(f".github/workflows/harness.yml 缺少 CI 检查命令：{token}")
    return issues


if __name__ == "__main__":
    sys.exit(main())
