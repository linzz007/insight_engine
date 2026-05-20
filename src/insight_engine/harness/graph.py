"""Harness Graph 模板。

Graph 只负责一件事：根据 State 决定下一步执行哪个阶段。
它不负责具体抓数据、清洗、分析、生成报告；这些具体动作放到对应 stage 或 agent 模块里。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from typing import Literal

from insight_engine.harness.hooks.stage_hooks import after_stage, before_stage
from insight_engine.harness.stage_gates import evaluate_stage_gate
from insight_engine.harness.state import InsightEngineState

# 定义这个项目允许出现哪些流程阶段
StageName = Literal[
    "initialized",
    "collect_raw_items",
    "clean_items",
    "structure_events",
    "analyze_insights",
    "generate_report",
    "review_and_eval",
    "done",
    "failed",
]

# 规定每个 stage 函数的统一形式。
# 好处是 Graph 不需要知道每个 stage 的具体参数，只要把同一个 state 传进去，再拿回一个更新后的 state。
StageHandler = Callable[[InsightEngineState], InsightEngineState]

# 表示 Graph 做出的一次流程判断。
@dataclass(frozen=True)
class GraphDecision:
    """Graph 每次判断后的结果。"""

    next_stage: StageName
    reason: str


class InsightEngineGraph:
    """最小 Harness 流程图。

    使用方式：

    1. 创建 `InsightEngineState`
    2. 注册每个 stage 对应的处理函数
    3. 调用 `run(state)`
    4. Graph 按顺序执行 stage，并根据 State 决定是否继续、重试或失败
    
    # graph主类，它代表整个 Harness 的流程控制器
    # 核心函数:run() decide_next_stage() _decide_after_review()
    """

    max_retry_count = 1
    max_stage_retry_count = int(os.getenv("HARNESS_STAGE_MAX_RETRY", "1"))
    # 注册每个 stage 对应的执行函数
    def __init__(self, handlers: dict[StageName, StageHandler]) -> None:
        self.handlers = handlers
   
    def run(self, state: InsightEngineState) -> InsightEngineState:
        """从当前 State 阶段开始运行，直到 done 或 failed。

        Graph 的执行引擎，它负责真正把流程跑起来

        只要当前 stage 不是 done 或 failed：
            1. 根据 State 判断下一步
            2. 把 State 的 current_stage 改成下一步
            3. 如果下一步是 done/failed，结束
            4. 找到这个 stage 对应的 handler
            5. 如果找不到 handler，失败
            6. 执行 before_stage hook
            7. 执行 handler
            8. 如果 handler 抛异常，记录错误并失败
            9. 如果 handler 成功，执行 after_stage hook
        返回最终 State
        
        
        
        """
        while state.current_stage not in {"done", "failed"}:
            decision = self.decide_next_stage(state)
            state.mark_stage(decision.next_stage)

            if decision.next_stage in {"done", "failed"}:
                break

            #根据 stage 名称找到具体执行函数。
            handler = self.handlers.get(decision.next_stage)
            if handler is None:
                state.add_error(
                    stage=decision.next_stage,
                    message="没有注册当前阶段的处理函数",
                    detail={"reason": decision.reason},
                )
                state.mark_stage("failed")
                break
            
            state = self._run_stage_with_gate(state, decision.next_stage, handler)
            if state.current_stage == "failed":
                break

        return state

    def _run_stage_with_gate(
        self,
        state: InsightEngineState,
        stage_name: StageName,
        handler: StageHandler,
    ) -> InsightEngineState:
        """运行一个 stage，并在 stage 结束后做 gate 检查。"""
        while True:
            hook_context = before_stage(state, stage_name)
            try:
                state = handler(state)
            except Exception as exc:  # noqa: BLE001
                after_stage(state, hook_context, error=repr(exc))
                state.add_error(
                    stage=stage_name,
                    message="阶段执行失败",
                    detail=repr(exc),
                )
                state.mark_stage("failed")
                return state

            gate_result = evaluate_stage_gate(state, stage_name)
            state.add_stage_gate_result(gate_result)
            state = after_stage(state, hook_context)

            if gate_result.get("passed"):
                return state

            current_retry_count = state.stage_retry_counts.get(stage_name, 0)
            can_retry = bool(gate_result.get("retryable")) and current_retry_count < self.max_stage_retry_count
            if not can_retry:
                state.add_error(
                    stage=stage_name,
                    message="stage gate 未通过",
                    detail=gate_result,
                )
                state.mark_stage("failed")
                return state

            retry_count = state.increment_stage_retry(stage_name)
            state.add_warning(
                stage=stage_name,
                message=f"stage gate 未通过，重跑当前 stage：第 {retry_count} 次",
                detail=gate_result,
            )

    def decide_next_stage(self, state: InsightEngineState) -> GraphDecision:
        """根据当前 State 判断下一步。

        这里是 Graph 的核心。你可以把它理解成“流程控制规则表”。
        """
        if state.current_stage == "initialized":
            return GraphDecision("collect_raw_items", "初始化完成，开始抓取原始信息")

        if state.current_stage == "collect_raw_items":
            if not state.global_raw_items and not state.ai_raw_items:
                return GraphDecision("failed", "没有抓取到原始信息")
            return GraphDecision("clean_items", "原始信息已存在，进入清洗阶段")

        if state.current_stage == "clean_items":
            if not state.global_cleaned_items and not state.ai_cleaned_items:
                return GraphDecision("failed", "清洗后没有可用信息")
            return GraphDecision("structure_events", "清洗结果已存在，进入结构化阶段")

        if state.current_stage == "structure_events":
            if not state.global_structured_events and not state.ai_structured_events:
                return GraphDecision("failed", "结构化记录为空")
            return GraphDecision("analyze_insights", "结构化记录已存在，进入分析阶段")

        if state.current_stage == "analyze_insights":
            if not state.analysis_result:
                return GraphDecision("failed", "分析结果为空")
            return GraphDecision("generate_report", "分析结果已存在，进入报告生成阶段")

        if state.current_stage == "generate_report":
            if not state.report_paths:
                return GraphDecision("failed", "报告路径为空")
            return GraphDecision("review_and_eval", "报告已生成，进入最终质量 hook 阶段")

        if state.current_stage == "review_and_eval":
            return self._decide_after_review(state)

        return GraphDecision("failed", f"未知阶段：{state.current_stage}")

    def _decide_after_review(self, state: InsightEngineState) -> GraphDecision:
        """根据 review/final quality hook 结果决定完成、重试或失败。"""
        quality_result = state.final_quality_result
        quality_passed = bool(quality_result.get("passed"))
        review_passed = bool(state.review_result.get("passed", True))

        if quality_passed and review_passed:
            return GraphDecision("done", "审查和最终质量 hook 通过")

        if state.retry_count >= self.max_retry_count:
            return GraphDecision("failed", "最终质量 hook 未通过，且已达到最大重试次数")

        state.retry_count += 1
        retry_stage = state.review_result.get("retry_stage") or quality_result.get("retry_stage")

        if retry_stage in {
            "structure_events",
            "analyze_insights",
            "generate_report",
        }:
            return GraphDecision(retry_stage, "最终质量 hook 未通过，返回指定阶段重试")

        return GraphDecision("analyze_insights", "最终质量 hook 未通过，默认回到分析阶段重试")


def build_graph(handlers: dict[StageName, StageHandler]) -> InsightEngineGraph:
    """创建 Graph 实例。

    后续 daily_news_report_skill 会调用这个函数，并传入真实 stage handler。
    """
    return InsightEngineGraph(handlers=handlers)
