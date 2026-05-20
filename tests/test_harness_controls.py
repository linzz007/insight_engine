import pytest

from insight_engine.harness.hooks.after_llm_call import parse_json_output, require_keys
from insight_engine.harness.tool_gateway import ToolGateway


def test_after_llm_call_parses_json_code_fence():
    payload = parse_json_output('```json\n{"passed": true, "score": 100}\n```')

    assert payload == {"passed": True, "score": 100}


def test_after_llm_call_requires_keys():
    require_keys({"passed": True}, ["passed"])

    with pytest.raises(ValueError):
        require_keys({"passed": True}, ["passed", "score"])


def test_tool_gateway_rejects_unallowed_tool():
    gateway = ToolGateway()

    with pytest.raises(PermissionError):
        gateway.call("clean_items", "fetch_source", object())
