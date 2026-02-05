import os
import json
from dotenv import load_dotenv

from app.mcp.client import MCPServerConfig

# Load env vars from .env file
load_dotenv()


def _parse_mcp_servers(raw: str | None) -> list[MCPServerConfig]:
    """Parse MCP_SERVERS JSON config."""
    if not raw:
        return []
    
    try:
        servers = json.loads(raw)
        return [MCPServerConfig(**s) for s in servers]
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Invalid MCP_SERVERS config: {e}")


class Settings:

    # App config
    APP_NAME: str = os.getenv("APP_NAME", "Simple AI agent")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 9201))
    API_VERSION: str = os.getenv("API_VERSION", "v1")

    # Logging
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Provider config
    PROVIDER: str = os.getenv("PROVIDER", "ollama")
    PROVIDER_BASE_URL: str = os.getenv("PROVIDER_BASE_URL", "http://localhost:11434")
    PROVIDER_API_KEY: str = os.getenv("PROVIDER_API_KEY", "-")

    # Model config
    MODEL: str = os.getenv("MODEL", "llama3.2")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.5))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", 3))

    # Response config
    RESPONSE_TYPE: str = os.getenv("RESPONSE_TYPE", "full")

    # Agent config
    SOME_USEFUL_VAR: str = os.getenv("SOME_USEFUL_VAR", "some_value")

    # MCP config
    MCP_SERVERS: list[MCPServerConfig] = _parse_mcp_servers(os.getenv("MCP_SERVERS"))
    MCP_TOOL_CALL_MAX_ITERATIONS: int = int(os.getenv("MCP_TOOL_CALL_MAX_ITERATIONS", 10))


settings = Settings()
