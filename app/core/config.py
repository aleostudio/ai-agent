import os
import json
from dotenv import load_dotenv
from app.mcp.client import MCPServerConfig

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

    # MCP config
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "False").lower() == "true"
    MCP_TOOL_CALL_MAX_ITERATIONS: int = int(os.getenv("MCP_TOOL_CALL_MAX_ITERATIONS", 10))

    def __init__(self):
        self.MCP_SERVERS: list[MCPServerConfig] = _parse_mcp_servers(
            os.getenv("MCP_SERVERS"), 
            self.MCP_ENABLED
        )


settings = Settings()
