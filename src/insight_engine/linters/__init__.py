"""Stage output linters.

每个文件对应一个 stage 的运行时产物检查规则。
Graph 仍然通过 stage_gates 调用这些 linter；linter 只负责判断，不负责执行 stage。
"""
