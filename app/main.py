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


# Build and manage application startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = AppRuntime()
    app.state.runtime = runtime

    print_banner()
    logger.info("Starting %s", settings.APP_NAME)

    model = init_chat_model(
        settings.MODEL,
        model_provider=settings.PROVIDER,
        base_url=settings.PROVIDER_BASE_URL,
        api_key=settings.PROVIDER_API_KEY,
        temperature=settings.TEMPERATURE,
        max_retries=settings.MAX_RETRIES,
    )

    if settings.MCP_ENABLED and settings.MCP_SERVERS:
        logger.info("MCP enabled, connecting to %s servers", len(settings.MCP_SERVERS))
        runtime.mcp_manager = MCPToolManager(settings.MCP_SERVERS)
        try:
            await runtime.mcp_manager.connect_all()
        except Exception as e:
            logger.error("Failed to connect MCP servers: %s", e)
            runtime.mcp_manager = None
    else:
        logger.info("MCP disabled, running without tools")

    extra_tools = []
    if settings.A2A_ENABLED and settings.A2A_ROLE == "orchestrator":
        from app.core.a2a.orchestrator import build_orchestrator_tools, fetch_agents_from_registry
        import app.prompts as prompts

        remote_agents = await fetch_agents_from_registry()
        if remote_agents:
            extra_tools = build_orchestrator_tools(remote_agents)
            agents_for_prompt = [
                {"name": a.get("card", {}).get("name", "unknown"), "description": a.get("card", {}).get("description", "")}
                for a in remote_agents
            ]
            system_prompt = prompts.build_system_prompt(
                "a2a_orchestrator",
                tool_names=[t.name for t in extra_tools],
                agents=agents_for_prompt,
            )
            runtime.agent = Agent(
                model,
                runtime.mcp_manager,
                system_prompt=system_prompt,
                extra_tools=extra_tools,
            )
            logger.info("A2A orchestrator initialized with %s routing tool(s)", len(extra_tools))
        else:
            logger.warning("No remote agents found, falling back to standard agent")
            runtime.agent = Agent(model, runtime.mcp_manager)
    else:
        runtime.agent = Agent(model, runtime.mcp_manager)

    if settings.A2A_ENABLED:
        from app.core.a2a import AgentA2AExecutor, create_a2a_starlette_app, register_with_registry

        agent_card = build_agent_card()
        agent_executor = AgentA2AExecutor(runtime.agent)
        a2a_app = create_a2a_starlette_app(agent_card, agent_executor)
        app.mount("", a2a_app)
        runtime.a2a_registration_task = asyncio.create_task(register_with_registry(settings.APP_URL))
        logger.info("A2A enabled (%s), registering on %s", settings.A2A_ROLE, settings.REGISTRY_URL)
    else:
        logger.info("A2A disabled")

    logger.info("===================================")
    logger.info("%s initialized", settings.APP_NAME)
    logger.info("===================================")
    yield

    logger.info("Shutting down application")

    if runtime.a2a_registration_task:
        runtime.a2a_registration_task.cancel()
        await asyncio.gather(runtime.a2a_registration_task, return_exceptions=True)

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
