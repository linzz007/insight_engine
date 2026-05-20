"""Stage Hooks。

Hook 的职责是记录、校验和转换阶段边界。
业务逻辑放在具体 stage 或 agent 模块里。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from insight_engine.harness.artifacts import ensure_run_dir, write_json_artifact
from insight_engine.harness.prompt_builder import build_prompt_package, should_build_prompt
from insight_engine.harness.state import InsightEngineState, utc_now_iso


@dataclass
class StageRunContext:
    """单次 stage 执行上下文。
    保存一个 stage 开始时的信息
    """

    stage_name: str
    started_at: str
    start_time: float


def before_stage(state: InsightEngineState, stage_name: str) -> StageRunContext:
    """
    stage 执行前做准备
    阶段执行前 Hook：按需生成 prompt 快照。

    1. build_prompt_package()
    2. 把 prompt 快照保存到 data/prompts/{run_id}/{stage}.md
    3. 把 prompt 路径写进 state.artifacts
    4. 返回 StageRunContext

    每个 stage 执行前，留下它当时“看到的上下文”。
    """
    if should_build_prompt(stage_name):
        prompt_package = build_prompt_package(stage_name=stage_name, state=state)
        prompt_dir = ensure_run_dir("data/prompts", state.run_id)
        prompt_path = prompt_dir / f"{stage_name}.md"
        prompt_path.write_text(prompt_package.prompt_text, encoding="utf-8")
        state.add_artifact(f"prompt:{stage_name}", str(prompt_path))

    return StageRunContext(
        stage_name=stage_name,
        started_at=utc_now_iso(),
        start_time=time.perf_counter(),
    )


def after_stage(
    state: InsightEngineState,
    context: StageRunContext,
    error: str | None = None,
) -> InsightEngineState:
    """
    stage 执行后记录结果

    1. 计算 stage 耗时
    2. 生成 trace
    3. 写入 state.stage_trace
    4. 保存 state snapshot 到 data/state/{run_id}/{stage}.json

    阶段执行后 Hook：记录 trace 并保存 State 快照。
    """
    finished_at = utc_now_iso()
    duration_ms = int((time.perf_counter() - context.start_time) * 1000)
    trace = {
        "stage": context.stage_name,
        "started_at": context.started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "status": "failed" if error else "ok",
        "error": error,
        "gate": _latest_gate_result(state, context.stage_name),
        "artifact_keys": sorted(state.artifacts.keys()),
    }
    state.add_stage_trace(trace)

    write_json_artifact(
        state=state,
        artifact_name=f"state_snapshot:{context.stage_name}",
        data=state.to_dict(),
        base_dir="data/state",
        filename=f"{context.stage_name}.json",
    )
    return state


def artifact_exists(path: str | None) -> bool:
    """检查 artifact 路径是否存在。"""
    return bool(path) and Path(path).exists()


def _latest_gate_result(state: InsightEngineState, stage_name: str) -> dict[str, Any] | None:
    for result in reversed(state.stage_gate_results):
        if result.get("stage") == stage_name:
            return result
    return None
