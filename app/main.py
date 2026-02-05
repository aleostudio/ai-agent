from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from langchain.chat_models import init_chat_model
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.model.simple_agent_request import SimpleAgentRequest
from app.mcp import MCPToolManager

# Avoid SSL verification
import truststore
truststore.inject_into_ssl()


# Global references
mcp_manager: MCPToolManager | None = None
simple_agent: SimpleAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestione lifecycle: connessione/disconnessione MCP servers."""
    global mcp_manager, simple_agent

    # Startup
    logger.info("Starting application...")

    # Init LLM
    model = init_chat_model(
        settings.MODEL,
        model_provider=settings.PROVIDER,
        base_url=settings.PROVIDER_BASE_URL,
        api_key=settings.PROVIDER_API_KEY,
        temperature=settings.TEMPERATURE,
        max_retries=settings.MAX_RETRIES
    )

    # Init MCP manager se configurato
    if settings.MCP_SERVERS:
        logger.info(f"Connecting to {len(settings.MCP_SERVERS)} MCP servers...")
        mcp_manager = MCPToolManager(settings.MCP_SERVERS)
        try:
            await mcp_manager.connect_all()
            logger.info(f"MCP servers connected: {mcp_manager.connected_servers}")
        except Exception as e:
            logger.error(f"Failed to connect MCP servers: {e}")
            mcp_manager = None
    else:
        logger.info("No MCP servers configured")

    # Init agent
    simple_agent = SimpleAgent(model, mcp_manager)
    logger.info("Agent initialized")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if mcp_manager:
        await mcp_manager.disconnect_all()
    logger.info("Shutdown complete")


# App init
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan
)


# API exposition
@app.post("/interact")
async def interact(request: SimpleAgentRequest):
    """Endpoint principale per interagire con l'agent."""
    if not simple_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        response_type = "ai_message"
        if settings.RESPONSE_TYPE == "text":
            response_type = "generated_text"

        response = await simple_agent.ainteract(request.prompt)
        logger.info(f"Prompt: {response['agent_response']['prompt']}")

        return {"response": response["agent_response"][response_type]}

    except Exception as e:
        logger.error(f"Error in /interact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check API
@app.get("/")
async def health_check():
    """Health check endpoint."""
    mcp_status = {
        "connected": mcp_manager.connected_servers if mcp_manager else [],
        "tools_count": len(mcp_manager.get_langchain_tools()) if mcp_manager and mcp_manager.is_initialized else 0
    }
    
    return {
        "status": "ok",
        "message": "Service is running",
        "mcp": mcp_status
    }


@app.get("/tools")
async def list_tools():
    """Lista tutti i tool MCP disponibili."""
    if not mcp_manager or not mcp_manager.is_initialized:
        return {"tools": []}

    tools = mcp_manager.get_langchain_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description
            }
            for t in tools
        ]
    }

