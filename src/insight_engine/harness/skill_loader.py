"""Skill Loader。

Skill 是“怎么做”的操作手册；executor 是“真的执行”的代码入口。
当前项目把日报能力收敛为一个总 Skill 和三个子 Skill：
- daily_news_report: 对话 Agent 可调用的完整日报能力
- data_preparation: 数据获取、清洗、结构化
- news_analysis: 洞察分析
- report_generation: 报告、图表、最终质量 hook
"""

from __future__ import annotations

from dataclasses import dataclass

from insight_engine.harness.artifacts import project_root


@dataclass(frozen=True)
class SkillPackage:
    """已加载的 Skill 文档。"""

    name: str
    path: str
    content: str


STAGE_SKILLS = {
    "structure_events": ["data_preparation"],
    "analyze_insights": ["news_analysis"],
    "generate_report": ["report_generation"],
    "review_and_eval": ["report_generation"],
}


def load_skill_by_name(skill_name: str) -> SkillPackage:
    """按名称加载一个 Skill 文档。"""
    relative_path = f"skills/{skill_name}/SKILL.md"
    path = project_root() / relative_path
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return SkillPackage(name=skill_name, path=relative_path, content=content)


def load_skills_for_stage(stage_name: str) -> list[SkillPackage]:
    """加载某个 stage 需要注入 prompt 的 Skill。"""
    return [load_skill_by_name(skill_name) for skill_name in STAGE_SKILLS.get(stage_name, [])]


def render_skill_context(stage_name: str) -> str:
    """把当前 stage 的 Skill 渲染成可放入 LLM prompt 的文本块。"""
    skills = load_skills_for_stage(stage_name)
    if not skills:
        return "本阶段没有配置额外 Skill。"

    sections: list[str] = []
    for skill in skills:
        sections.extend(
            [
                f"### {skill.name}",
                f"- path: `{skill.path}`",
                "",
                skill.content.strip() or "Skill 文件为空。",
                "",
            ]
        )
    return "\n".join(sections).strip()

