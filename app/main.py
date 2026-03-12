import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain.chat_models import init_chat_model
import truststore
import uvicorn
from app.a2a_card import build_agent_card
from app.agent.agent import Agent
from app.api import router as api_router
from app.config import settings
from app.core.logger import logger
from app.core.banner import print_banner
from app.core.mcp import MCPToolManager
from app.core.runtime import AppRuntime


# Use system trust store certificates
truststore.inject_into_ssl()


# Check if A2A is enabled if HTTP API is disabled
if not settings.HTTP_API_ENABLED and not settings.A2A_ENABLED:
    raise RuntimeError("HTTP_API_ENABLED=False requires A2A_ENABLED=True")


# Build orchestrator agent instance and signature from current registry state
async def _build_orchestrator_agent(model, mcp_manager):
    from app.core.a2a.orchestrator import build_orchestrator_tools, fetch_agents_from_registry
    import app.prompts as prompts

    remote_agents = await fetch_agents_from_registry()
    if not remote_agents:
        return Agent(model, mcp_manager), ""

    extra_tools = build_orchestrator_tools(remote_agents)
    agents_for_prompt = [
        {
            "name": a.get("card", {}).get("name", "unknown"),
            "description": a.get("card", {}).get("description", ""),
        }
        for a in remote_agents
    ]
    signature = "|".join(sorted(f"{a.get('url', '')}::{a.get('card', {}).get('name', '')}" for a in remote_agents))
    system_prompt = prompts.build_system_prompt(
        "a2a_orchestrator",
        tool_names=[t.name for t in extra_tools],
        agents=agents_for_prompt,
    )

    return Agent(model, mcp_manager, system_prompt=system_prompt, extra_tools=extra_tools), signature


# Refresh orchestrator routing tools by polling registry at runtime
async def _orchestrator_refresh_loop(runtime: AppRuntime, model) -> None:
    if not settings.ORCHESTRATOR_REFRESH_ENABLED:
        logger.info("Orchestrator refresh loop disabled")
        return

    interval = max(settings.ORCHESTRATOR_REFRESH_INTERVAL_S, 10.0)
    logger.info("Orchestrator refresh loop enabled: every %ss", interval)

    while True:
        try:
            refreshed_agent, signature = await _build_orchestrator_agent(model, runtime.mcp_manager)
            if signature != runtime.orchestrator_agents_signature:
                runtime.agent = refreshed_agent
                runtime.orchestrator_agents_signature = signature
                logger.info("Orchestrator routing table refreshed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Orchestrator refresh failed: %s", e)

        await asyncio.sleep(interval)


# Build the configured chat model
def _create_model():
    return init_chat_model(
        settings.MODEL,
        model_provider=settings.PROVIDER,
        base_url=settings.PROVIDER_BASE_URL,
        api_key=settings.PROVIDER_API_KEY,
        temperature=settings.TEMPERATURE,
        max_retries=settings.MAX_RETRIES,
    )


# Initialize MCP manager if enabled
async def _initialize_mcp(runtime: AppRuntime) -> None:
    if not settings.MCP_ENABLED or not settings.MCP_SERVERS:
        logger.info("MCP disabled, running without tools")
        return

    logger.info("MCP enabled, connecting to %s servers", len(settings.MCP_SERVERS))
    runtime.mcp_manager = MCPToolManager(settings.MCP_SERVERS)
    try:
        await runtime.mcp_manager.connect_all()
    except Exception as e:
        logger.error("Failed to connect MCP servers: %s", e)
        runtime.mcp_manager = None


# Initialize agent runtime (standard or orchestrator)
async def _initialize_agent(runtime: AppRuntime, model) -> None:
    if settings.A2A_ENABLED and settings.A2A_ROLE == "orchestrator":
        runtime.agent, runtime.orchestrator_agents_signature = await _build_orchestrator_agent(model, runtime.mcp_manager)
        if runtime.orchestrator_agents_signature:
            logger.info("A2A orchestrator initialized with dynamic routing")
        else:
            logger.warning("No remote agents found, falling back to standard agent")

        runtime.orchestrator_refresh_task = asyncio.create_task(_orchestrator_refresh_loop(runtime, model))
        return

    runtime.agent = Agent(model, runtime.mcp_manager)


# Mount A2A server and start registry polling if enabled
def _initialize_a2a(runtime: AppRuntime, app: FastAPI) -> None:
    if not settings.A2A_ENABLED:
        logger.info("A2A disabled")
        return

    from app.core.a2a import AgentA2AExecutor, create_a2a_starlette_app, registration_poll_loop

    agent_card = build_agent_card()
    agent_executor = AgentA2AExecutor(lambda: runtime.agent)
    a2a_app = create_a2a_starlette_app(agent_card, agent_executor)
    app.mount("", a2a_app)
    if settings.A2A_REGISTER_ENABLED:
        runtime.a2a_registry_poll_task = asyncio.create_task(registration_poll_loop(settings.APP_URL))
        logger.info("A2A enabled (%s), registration enabled on %s", settings.A2A_ROLE, settings.REGISTRY_URL)
    else:
        logger.info("A2A enabled (%s), registration disabled", settings.A2A_ROLE)


# Cancel a background task safely
async def _cancel_task(task: asyncio.Task | None) -> None:
    if not task:
        return

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


# Build and manage application startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = AppRuntime()
    app.state.runtime = runtime

    print_banner()
    logger.info("Starting %s", settings.APP_NAME)

    model = _create_model()
    await _initialize_mcp(runtime)
    await _initialize_agent(runtime, model)
    _initialize_a2a(runtime, app)

    logger.info("===================================")
    logger.info("%s initialized", settings.APP_NAME)
    logger.info("===================================")
    yield

    logger.info("Shutting down application")
    await _cancel_task(runtime.a2a_registry_poll_task)
    await _cancel_task(runtime.orchestrator_refresh_task)

    if runtime.mcp_manager:
        await runtime.mcp_manager.disconnect_all()

    logger.info("Shutdown complete")


# FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=None if not settings.HTTP_API_ENABLED else "/docs",
    redoc_url=None if not settings.HTTP_API_ENABLED else "/redoc",
    openapi_url=None if not settings.HTTP_API_ENABLED else "/openapi.json",
)


# Load routes if enabled
if settings.HTTP_API_ENABLED:
    app.include_router(api_router)


# App launch if invoked directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, log_level="warning")
