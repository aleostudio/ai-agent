from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from langchain.chat_models import init_chat_model
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.model.simple_agent_request import SimpleAgentRequest
from app.mcp import MCPToolManager
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

    # Init agent
    simple_agent = SimpleAgent(model, mcp_manager)
    logger.info("Agent initialized")

    # Pause: here we are handling HTTP requests, waiting for shutdown
    yield

    # Shutdown
    logger.info("Shutting down application")
    if mcp_manager:
        await mcp_manager.disconnect_all()
    logger.info("Shutdown complete")


# App init
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan
)


# Interact API
@app.post("/interact")
async def interact(request: SimpleAgentRequest):
    if not simple_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        response_type = "ai_message"
        if settings.RESPONSE_TYPE == "text":
            response_type = "generated_text"

        response = await simple_agent.async_interact(request.prompt)

        return {
            "response": response["agent_response"][response_type]
        }

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
    
    response = {
        "status": "ok",
        "message": "Service is running",
    }
    
    if mcp_status:
        response["mcp"] = mcp_status
    
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


# App launch if invoked directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, log_level="warning")
