import asyncio
import json
from app.core.tool_runtime import AgentToolRuntime


class FakeModel:
    def __init__(self):
        self.bound_tools = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self


class FakeExtraTool:
    def __init__(self, name="a2a__echo"):
        self.name = name

    async def ainvoke(self, args):
        await asyncio.sleep(0)
        return {"echo": args}


class FakeMCPManager:
    is_initialized = True

    def __init__(self):
        self.called = None

    def get_langchain_tools(self):
        class _Tool:
            name = "mcp__sum"
        return [_Tool()]

    async def call_tool(self, tool_name, tool_args):
        await asyncio.sleep(0)
        self.called = (tool_name, tool_args)
        return {"ok": True}


def test_has_tools_with_extra_tool():
    rt = AgentToolRuntime(mcp_manager=None, extra_tools=[FakeExtraTool()])
    assert rt.has_tools is True


def test_bind_model_binds_tools():
    rt = AgentToolRuntime(mcp_manager=None, extra_tools=[FakeExtraTool()])
    model = FakeModel()
    rt.bind_model(model)
    assert model.bound_tools is not None
    assert len(model.bound_tools) == 1


def test_execute_tool_call_with_extra_tool():
    rt = AgentToolRuntime(mcp_manager=None, extra_tools=[FakeExtraTool()])
    out = asyncio.run(rt.execute_tool_calls([{"id": "1", "name": "a2a__echo", "args": {"x": 1}}]))
    payload = json.loads(out[0].content)
    assert payload["echo"]["x"] == 1


def test_execute_tool_call_with_mcp_tool():
    mcp = FakeMCPManager()
    rt = AgentToolRuntime(mcp_manager=mcp, extra_tools=[])
    out = asyncio.run(rt.execute_tool_calls([{"id": "2", "name": "mcp__sum", "args": {"a": 2}}]))
    payload = json.loads(out[0].content)
    assert payload["ok"] is True
    assert mcp.called == ("mcp__sum", {"a": 2})
