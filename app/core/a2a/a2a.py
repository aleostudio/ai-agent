import asyncio
import httpx
from starlette.applications import Starlette
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard, TaskState, TaskStatus, TaskStatusUpdateEvent
from a2a.utils.message import new_agent_text_message
from app.core.config import settings
from app.core.logger import logger


# A2A AgentExecutor that wraps our SimpleAgent
class SimpleAgentExecutor(AgentExecutor):

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


# Register this agent with the A2A registry
async def register_with_registry(agent_url: str) -> None:
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{settings.REGISTRY_URL}/register", json={"url": agent_url}, timeout=settings.REGISTRY_TIMEOUT_S)
            resp.raise_for_status()
            logger.info("A2A client: registered with A2A registry: %s", resp.json())
        except Exception as e:
            logger.warning("Could not register with A2A registry: %s", e)


# Build the A2A Starlette sub-application
def create_a2a_starlette_app(agent_card: AgentCard, agent_executor: AgentExecutor) -> Starlette:
    handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)

    return a2a_app.build()
