import asyncio
import httpx
from starlette.applications import Starlette
from a2a.server.agent_execution.agent_executor import AgentExecutor as BaseA2AExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard, TaskState, TaskStatus, TaskStatusUpdateEvent
from a2a.utils.message import new_agent_text_message
from app.config import settings
from app.core.logger import logger


# A2A executor that wraps our local Agent runtime.
class AgentA2AExecutor(BaseA2AExecutor):

    def __init__(self, agent):
        self.agent = agent


    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        task_id = context.task_id
        context_id = context.context_id

        try:
            # Mark task as working
            await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=task_id, context_id=context_id, status=TaskStatus(state=TaskState.working), final=False))

            # Run our agent
            result = await self.agent.async_interact(user_input)
            response_text = result["agent_response"].get("generated_text") or ""

            # If generated_text is empty, try extracting from ai_message
            if not response_text:
                ai_message = result["agent_response"].get("ai_message")
                if ai_message and hasattr(ai_message, "content"):
                    response_text = ai_message.content

            # Send completed status with the response message
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.completed, message=new_agent_text_message(text=response_text, task_id=task_id, context_id=context_id)),
                    final=True,
                )
            )

        except Exception as e:
            logger.error(f"A2A execute error: {e}")
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.failed, message=new_agent_text_message(text=f"Error: {e}", task_id=task_id, context_id=context_id)),
                    final=True,
                )
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=context.task_id, context_id=context.context_id, status=TaskStatus(state=TaskState.canceled), final=True))


# Check whether the current agent URL is already present in registry.
async def is_registered_in_registry(agent_url: str) -> bool:
    normalized = agent_url.rstrip("/")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.REGISTRY_URL}/agents", timeout=settings.REGISTRY_TIMEOUT_S)
        resp.raise_for_status()
        agents = resp.json()

        return any(a.get("url", "").rstrip("/") == normalized for a in agents)


# Register this agent with the A2A registry
async def register_with_registry(agent_url: str) -> None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{settings.REGISTRY_URL}/register", json={"url": agent_url}, timeout=settings.REGISTRY_TIMEOUT_S)
            resp.raise_for_status()
            logger.info("A2A client: registered with A2A registry: %s", resp.json())
        except Exception as e:
            logger.warning("Could not register with A2A registry: %s", e)


# Keep registration alive by periodically checking registry and re-registering if missing.
async def registration_poll_loop(agent_url: str) -> None:
    if not settings.REGISTRY_POLL_ENABLED:
        logger.info("A2A registry polling disabled")
        return

    interval = max(settings.REGISTRY_POLL_INTERVAL_S, 5.0)
    logger.info("A2A registry polling enabled: every %ss", interval)

    while True:
        try:
            registered = await is_registered_in_registry(agent_url)
            if not registered:
                logger.warning("Agent missing from registry, attempting re-registration")
                await register_with_registry(agent_url)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("A2A registry poll failed: %s", e)

        await asyncio.sleep(interval)


# Build the A2A Starlette sub-application.
def create_a2a_starlette_app(agent_card: AgentCard, agent_executor: BaseA2AExecutor) -> Starlette:
    handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

    return a2a_app.build()
