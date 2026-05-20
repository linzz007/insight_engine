"""Tool Gateway。

Tool Gateway 控制每个 stage 能调用哪些工具函数。
Agent 不应该随意调用任意工具；先经过这个网关，后续才方便审计和限制权限。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from insight_engine.tools.quality_check import check_quality

#工具函数可以接收任意参数，返回任意结果。
ToolFn = Callable[..., Any]


@dataclass(frozen=True)
class ToolCallRecord:
    """工具调用记录。
    记录一次工具调用。

    stage_name  哪个 stage 发起调用
    tool_name   调用了哪个工具
    allowed     这次调用是否被允许
    """

    stage_name: str
    tool_name: str
    allowed: bool

# 注册系统里有哪些工具，工具白名单总表
TOOL_REGISTRY: dict[str, ToolFn] = {
    "check_quality": check_quality,
}

# 定义每个 stage 允许调用哪些工具。
STAGE_ALLOWED_TOOLS = {
    "review_and_eval": {"check_quality"},
}


class ToolGateway:
    """受控工具调用入口。"""

    def __init__(self) -> None:
        self.calls: list[ToolCallRecord] = []

    def call(self, stage_name: str, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        """调用工具。未授权时抛出异常。
        
        判断这个 stage 是否允许调用这个 tool。
        记录调用。
        如果不允许，抛出权限错误。
        如果允许，从 registry 找到函数并执行。
        
        """
        allowed = tool_name in STAGE_ALLOWED_TOOLS.get(stage_name, set())
        self.calls.append(ToolCallRecord(stage_name=stage_name, tool_name=tool_name, allowed=allowed))

        if not allowed:
            raise PermissionError(f"stage `{stage_name}` 不允许调用工具 `{tool_name}`")

        tool = TOOL_REGISTRY.get(tool_name)
        if tool is None:
            raise KeyError(f"工具不存在：{tool_name}")
        return tool(*args, **kwargs)
