import json
import os
from enum import StrEnum
from dotenv import load_dotenv
from app.core.mcp.client import MCPServerConfig


# Load env vars from .env file
load_dotenv()


# Parse MCP servers if enabled
def _parse_mcp_servers(raw: str | None, enabled: bool) -> list[MCPServerConfig]:
    if not enabled or not raw:
        return []
    try:
        servers = json.loads(raw)
        return [MCPServerConfig(**s) for s in servers]
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Invalid MCP_SERVERS config: {e}")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class A2ARole(StrEnum):
    CLIENT = "client"
    ORCHESTRATOR = "orchestrator"


class ResponseType(StrEnum):
    FULL = "full"
    TEXT = "text"
    STREAM = "stream"


class Settings:

    # App config
    APP_NAME: str = os.getenv("APP_NAME", "AI agent")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 9201))
    APP_VERSION: str = os.getenv("APP_VERSION", "v1")
    APP_URL: str = os.getenv("APP_URL", f"http://localhost:{APP_PORT}")

    # Logging
    DEBUG: bool = _get_bool("DEBUG", False)

    # Provider config
    PROVIDER: str = os.getenv("PROVIDER", "ollama")
    PROVIDER_BASE_URL: str = os.getenv("PROVIDER_BASE_URL", "http://localhost:11434")
    PROVIDER_API_KEY: str = os.getenv("PROVIDER_API_KEY", "-")

    # Model config
    MODEL: str = os.getenv("MODEL", "llama3.2")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.5))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 3))

    # Response config
    RESPONSE_TYPE: ResponseType = ResponseType(os.getenv("RESPONSE_TYPE", "full").lower())

    # MCP config
    MCP_ENABLED: bool = _get_bool("MCP_ENABLED", False)

    # Tool calling config (applies to both MCP and A2A routing tools)
    TOOL_CALL_MAX_ITERATIONS: int = int(os.getenv("TOOL_CALL_MAX_ITERATIONS", os.getenv("MCP_TOOL_CALL_MAX_ITERATIONS", 10)))

    # HTTP API config
    HTTP_API_ENABLED: bool = _get_bool("HTTP_API_ENABLED", True)

    # A2A config
    A2A_ENABLED: bool = _get_bool("A2A_ENABLED", False)
    A2A_ROLE: A2ARole = A2ARole(os.getenv("A2A_ROLE", "client").lower())
    REGISTRY_URL: str = os.getenv("REGISTRY_URL", "http://localhost:9300")
    REGISTRY_TIMEOUT_S: float = float(os.getenv("REGISTRY_TIMEOUT_S", "4.0"))

    def __init__(self):
        self.MCP_SERVERS: list[MCPServerConfig] = _parse_mcp_servers(
            os.getenv("MCP_SERVERS"), 
            self.MCP_ENABLED
        )


settings = Settings()
