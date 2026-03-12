import asyncio
from langchain_core.messages import AIMessage, HumanMessage
from app.agent.agent import Agent
from app.config import settings


class FakeModel:
    def __init__(self):
        self.calls = []

    async def ainvoke(self, messages):
        await asyncio.sleep(0)
        self.calls.append(messages)
        return AIMessage(content="ok")


async def _run_memory_flow():
    model = FakeModel()
    agent = Agent(model, mcp_manager=None)

    await agent.async_interact("hello", session_id="s1")
    await agent.async_interact("again", session_id="s1")

    return model.calls


def test_agent_session_memory(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_ENABLED", True)
    monkeypatch.setattr(settings, "MEMORY_TTL_S", 1800.0)
    monkeypatch.setattr(settings, "MEMORY_MAX_SESSIONS", 10)
    monkeypatch.setattr(settings, "MEMORY_MAX_MESSAGES", 20)

    calls = asyncio.run(_run_memory_flow())
    second_call = calls[1]

    # First call has system + current human; second call should include history.
    assert any(isinstance(m, HumanMessage) and m.content == "hello" for m in second_call)
    assert any(isinstance(m, AIMessage) and m.content == "ok" for m in second_call)
