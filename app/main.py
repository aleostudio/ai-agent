from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain.chat_models import init_chat_model
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.model.simple_agent_request import SimpleAgentRequest
from app.core.mcp import MCPToolManager
from app.a2a_card import build_agent_card
import asyncio
import uvicorn

# Avoid SSL verification
import truststore
truststore.inject_into_ssl()


# Global references
mcp_manager = None
simple_agent: SimpleAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_manager, simple_agent

    logger.info("Starting agent")

    # Init LLM
    model = init_chat_model(
        settings.MODEL,
        model_provider=settings.PROVIDER,
        base_url=settings.PROVIDER_BASE_URL,
        api_key=settings.PROVIDER_API_KEY,
        temperature=settings.TEMPERATURE,
        max_retries=settings.MAX_RETRIES
    )

    # Init MCP manager if enabled
    if settings.MCP_ENABLED and settings.MCP_SERVERS:
        logger.info(f"MCP enabled, connecting to {len(settings.MCP_SERVERS)} servers")
        mcp_manager = MCPToolManager(settings.MCP_SERVERS)
        try:
            await mcp_manager.connect_all()
        except Exception as e:
            logger.error(f"Failed to connect MCP servers: {e}")
            mcp_manager = None
    else:
        logger.info("MCP disabled, running without tools")

    # Init agent — branch on A2A role
    a2a_registration_task = None
    extra_tools = []

    if settings.A2A_ENABLED and settings.A2A_ROLE == "orchestrator":
        from app.core.a2a.orchestrator import fetch_agents_from_registry, build_orchestrator_tools
        import app.prompts as prompts

        remote_agents = await fetch_agents_from_registry()
        if remote_agents:
            extra_tools = build_orchestrator_tools(remote_agents)
            agents_for_prompt = [
                {"name": a["card"]["name"], "description": a["card"].get("description", "")}
                for a in remote_agents
            ]
            system_prompt = prompts.build_system_prompt("a2a_orchestrator", tool_names=[t.name for t in extra_tools], agents=agents_for_prompt)
            simple_agent = SimpleAgent(model, mcp_manager, system_prompt=system_prompt, extra_tools=extra_tools)
            logger.info(f"A2A orchestrator initialized with {len(extra_tools)} routing tool(s)")
        else:
            logger.warning("No remote agents found, falling back to standard agent")
            simple_agent = SimpleAgent(model, mcp_manager)
    else:
        simple_agent = SimpleAgent(model, mcp_manager)

    logger.info("Agent initialized")

    # Mount A2A sub-application if enabled (both client and orchestrator serve the A2A endpoint)
    if settings.A2A_ENABLED:
        from app.core.a2a import SimpleAgentExecutor, create_a2a_starlette_app, build_agent_card, register_with_registry

        agent_card = build_agent_card()
        agent_executor = SimpleAgentExecutor(simple_agent)
        a2a_app = create_a2a_starlette_app(agent_card, agent_executor)
        app.mount("", a2a_app)
        a2a_registration_task = asyncio.create_task(register_with_registry(settings.APP_URL))
        logger.info(f"A2A enabled ({settings.A2A_ROLE}), registering on {settings.REGISTRY_URL}")
    else:
        logger.info("A2A disabled")

    # Pause: here we are handling HTTP requests, waiting for shutdown
    yield

    # Cancel A2A registration task if still running
    if a2a_registration_task:
        a2a_registration_task.cancel()
        await asyncio.gather(a2a_registration_task, return_exceptions=True)

    # Shutdown
    logger.info("Shutting down application")
    if mcp_manager:
        await mcp_manager.disconnect_all()
    logger.info("Shutdown complete")


# App init
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)


# Interact API
@app.post("/interact", responses={503: {"description": "Agent not initialized"}, 500: {"description": "Internal server error"}})
async def interact(request: SimpleAgentRequest):
    if not simple_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Streaming mode
        if settings.RESPONSE_TYPE == "stream":
            return StreamingResponse(simple_agent.stream_interact(request.prompt), media_type="text/event-stream")

        # Sync modes
        response_type = "ai_message" if settings.RESPONSE_TYPE == "full" else "generated_text"
        response = await simple_agent.async_interact(request.prompt)

        return {"response": response["agent_response"][response_type]}

    except Exception as e:
        logger.error(f"Interact API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health API
@app.get("/")
async def health_check():
    mcp_status = None
    if settings.MCP_ENABLED and mcp_manager:
        mcp_status = {
            "connected": mcp_manager.connected_servers,
            "tools_count": len(mcp_manager.get_langchain_tools()) if mcp_manager.is_initialized else 0
        }

    a2a_status = None
    if settings.A2A_ENABLED:
        a2a_status = {"registry": settings.REGISTRY_URL}

    response = {"status": "ok", "message": "Service is running"}

    if mcp_status:
        response["mcp"] = mcp_status

    if a2a_status:
        response["a2a"] = a2a_status

    return response


# MCP tools list API
@app.get("/tools")
async def list_tools():
    if not settings.MCP_ENABLED:
        return {"enabled": False, "tools": []}

    if not mcp_manager or not mcp_manager.is_initialized:
        return {"enabled": True, "connected": False, "tools": []}

    tools = mcp_manager.get_langchain_tools()
    return {
        "enabled": True,
        "connected": True,
        "tools": [{"name": t.name, "description": t.description} for t in tools]
    }


# Web UI to test model
@app.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    ui_path = Path(__file__).parent.parent / "ui" / "index.html"
    return HTMLResponse(ui_path.read_text(encoding="utf-8"))


# App launch if invoked directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, log_level="warning")
