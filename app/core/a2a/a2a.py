import asyncio
import httpx
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard
from app.core.config import REGISTRY_TIMEOUT_S, REGISTRY_URL
from app.core.logger import logger


# Register this agent with the A2A registry after a short delay
async def register_with_registry(agent_url: str) -> None:
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{REGISTRY_URL}/register", json={"url": agent_url}, timeout=REGISTRY_TIMEOUT_S)
            resp.raise_for_status()
            logger.info("Registered with registry: %s", resp.json())

        except Exception as e:
            logger.warning("Could not register with registry: %s", e)


def create_lifespan(agent_url: str):
    @asynccontextmanager
    async def lifespan(app: Starlette):
        task = asyncio.create_task(register_with_registry(agent_url))
        yield
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    return lifespan


def create_a2a_starlette_app(agent_card: AgentCard, agent_executor: AgentExecutor, agent_url: str) -> Starlette:
    handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

    return a2a_app.build(lifespan=create_lifespan(agent_url))
