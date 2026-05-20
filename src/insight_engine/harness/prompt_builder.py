"""Prompt Builder。

即使 V1 的主体逻辑是规则代码，也保留 prompt 组装能力。
这样后续替换为 LLM Agent 时，不需要重写 Harness。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from insight_engine.harness.context_router import build_context_package, read_context_file
from insight_engine.harness.skill_loader import load_skills_for_stage
from insight_engine.harness.state import InsightEngineState

PROMPTLESS_STAGES = {"collect_raw_items", "clean_items"}


@dataclass(frozen=True)
class PromptPackage:
    """某个 stage 的完整 prompt 包。
    
    stage_name          当前 stage 名称
    prompt_text         最终拼好的完整 prompt
    context_paths       本次用了哪些文档
    skill_paths         本次用了哪些 skill
    visible_state_keys  本次暴露了哪些 State 字段
    """

    stage_name: str
    prompt_text: str
    context_paths: list[str]
    skill_paths: list[str]
    visible_state_keys: list[str]


def build_prompt_package(stage_name: str, state: InsightEngineState) -> PromptPackage:
    """组装 stage prompt。"""
    context = build_context_package(stage_name=stage_name, state=state)
    skills = load_skills_for_stage(stage_name)

    sections: list[str] = [
        f"# Stage Prompt: {stage_name}",
        "",
        "## Agent Role",
        read_context_file(context.agent_prompt_path),
        "",
        "## Runtime Documents",
    ]

    for doc_path in context.runtime_doc_paths:
        sections.extend([f"### {doc_path}", read_context_file(doc_path), ""])

    sections.append("## Skills")
    for skill in skills:
        sections.extend([f"### {skill.path}", skill.content, ""])

    sections.extend(
        [
            "## Visible State",
            "```json",
            json.dumps(context.visible_state, ensure_ascii=False, indent=2, default=str),
            "```",
            "",
            "## Output Requirement",
            "请严格产出当前 stage 对应的结构化结果，并保留可追踪证据。",
            "",
        ]
    )

    return PromptPackage(
        stage_name=stage_name,
        prompt_text="\n".join(sections),
        context_paths=[context.agent_prompt_path, *context.runtime_doc_paths],
        skill_paths=[skill.path for skill in skills],
        visible_state_keys=list(context.visible_state.keys()),
    )


def should_build_prompt(stage_name: str) -> bool:
    """判断当前 stage 是否需要生成 LLM prompt 快照。"""
    return stage_name not in PROMPTLESS_STAGES
