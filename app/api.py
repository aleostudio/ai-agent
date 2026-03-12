from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from app.config import ResponseType, settings
from app.core.logger import logger
from app.core.runtime import AppRuntime

router = APIRouter()


# Request validation
class AgentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt")
    session_id: str | None = Field(default=None, description="Optional session id for memory")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty")

        return cleaned


# Return app runtime from FastAPI state, creating an empty fallback for tests
def _runtime_from_request(request: Request) -> AppRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        runtime = AppRuntime()
        request.app.state.runtime = runtime

    return runtime


# Handle agent interaction over HTTP
@router.post("/interact", responses={503: {"description": "Agent not initialized"}, 500: {"description": "Internal server error"}})
async def interact(request: AgentRequest, http_request: Request):
    runtime = _runtime_from_request(http_request)
    if not runtime.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        if settings.RESPONSE_TYPE == ResponseType.STREAM:
            return StreamingResponse(runtime.agent.stream_interact(request.prompt, session_id=request.session_id), media_type="text/event-stream")
        response_type = "ai_message" if settings.RESPONSE_TYPE == ResponseType.FULL else "generated_text"
        response = await runtime.agent.async_interact(request.prompt, session_id=request.session_id)

        return {
            "response": response["agent_response"][response_type]
        }

    except Exception as e:
        logger.exception("Interact API error")
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Report application health and optional MCP/A2A status
@router.get("/")
async def health_check(http_request: Request):
    runtime = _runtime_from_request(http_request)
    mcp_status = None
    if settings.MCP_ENABLED and runtime.mcp_manager:
        mcp_status = {
            "connected": runtime.mcp_manager.connected_servers,
            "tools_count": len(runtime.mcp_manager.get_langchain_tools()) if runtime.mcp_manager.is_initialized else 0,
        }

    a2a_status = None
    if settings.A2A_ENABLED:
        a2a_status = {
            "registry": settings.REGISTRY_URL,
            "role": settings.A2A_ROLE
        }

    response = {
        "status": "ok",
        "message": "Service is running",
        "http_api_enabled": settings.HTTP_API_ENABLED
    }

    if mcp_status:
        response["mcp"] = mcp_status

    if a2a_status:
        response["a2a"] = a2a_status

    return response


# List all available MCP and A2A routing tools
@router.get("/tools")
async def list_tools(http_request: Request):
    runtime = _runtime_from_request(http_request)
    tools_list = []

    if settings.MCP_ENABLED and runtime.mcp_manager and runtime.mcp_manager.is_initialized:
        tools_list.extend(
            {"name": t.name, "description": t.description, "source": "mcp"}
            for t in runtime.mcp_manager.get_langchain_tools()
        )

    if runtime.agent:
        tools_list.extend(
            {"name": t.name, "description": t.description, "source": "a2a"}
            for t in runtime.agent.extra_tools
        )

    return {"tools": tools_list}


# Serve the local debug UI page
@router.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    ui_path = Path(__file__).resolve().parents[1] / "ui" / "index.html"

    return HTMLResponse(ui_path.read_text(encoding="utf-8"))
