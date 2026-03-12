import asyncio
from dataclasses import dataclass
from app.agent.agent import Agent
from app.core.mcp import MCPToolManager


@dataclass
class AppRuntime:
    agent: Agent | None = None
    mcp_manager: MCPToolManager | None = None
    a2a_registry_poll_task: asyncio.Task | None = None
    orchestrator_refresh_task: asyncio.Task | None = None
    orchestrator_agents_signature: str = ""
