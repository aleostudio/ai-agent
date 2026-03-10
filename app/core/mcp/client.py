import logging
from typing import Any
from dataclasses import dataclass, field
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import Tool as MCPTool

# Global logger
logger = logging.getLogger(__name__)


# MCP server configuration
@dataclass
class MCPServerConfig:
    name: str
    transport: str                                 # "sse" | "stdio"
    url: str | None = None                         # For SSE
    command: str | None = None                     # For STDIO
    args: list[str] = field(default_factory=list)  # For STDIO
    env: dict[str, str] | None = None              # For STDIO
    timeout: float = 30.0
    enabled: bool = True


    def __post_init__(self):
        if self.transport == "sse" and not self.url:
            raise ValueError(f"Server '{self.name}': SSE transport requires 'url'")

        if self.transport == "stdio" and not self.command:
            raise ValueError(f"Server '{self.name}': STDIO transport requires 'command'")


# MCP client via SSE or STDIO
class MCPClient:

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: ClientSession | None = None
        self._tools: list[MCPTool] = []
        self._connected = False

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[MCPTool]:
        return self._tools


    # Connect to the MCP server
    async def connect(self) -> None:
        if self._connected:
            await self.disconnect()

        try:
            if self.config.transport == "sse":
                await self._connect_sse()
            elif self.config.transport == "stdio":
                await self._connect_stdio()
            else:
                raise ValueError(f"Transport not supported: {self.config.transport}")

            # Get available tools
            await self._load_tools()
            self._connected = True
            logger.info(f"MCP server '{self.name}' connected, {len(self._tools)} tools available")

        except Exception as e:
            self._connected = False
            logger.error(f"[{self.name}] Connection failed: {e}")
            raise


    # SSE connection
    async def _connect_sse(self) -> None:
        self._sse_context = sse_client(url=self.config.url)
        streams = await self._sse_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()


    # STDIO connection
    async def _connect_stdio(self) -> None:
        server_params = StdioServerParameters(command=self.config.command, args=self.config.args, env=self.config.env)
        self._stdio_context = stdio_client(server_params)
        streams = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()


    # Get tools list
    async def _load_tools(self) -> None:
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        result = await self.session.list_tools()
        self._tools = result.tools


    # Invoke MCP tool by name
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError(f"[{self.name}] Not connected")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Extract MCP response
            if result.content:
                contents = []
                for block in result.content:
                    if hasattr(block, 'text'):
                        contents.append(block.text)
                    elif hasattr(block, 'data'):
                        contents.append(block.data)
                
                return contents[0] if len(contents) == 1 else contents
            
            return None
            
        except Exception as e:
            # Connection lost
            self._connected = False
            self.session = None
            logger.warning(f"[{self.name}] Connection lost: {e}")
            raise RuntimeError(f"MCP server '{self.name}' disconnected")


    # Disconnect
    async def disconnect(self) -> None:
        if not self._connected:
            return

        self._connected = False
        self.session = None

        try:
            if hasattr(self, '_session_context') and self._session_context:
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception:
                    pass
            
            if self.config.transport == "sse" and hasattr(self, '_sse_context') and self._sse_context:
                try:
                    await self._sse_context.__aexit__(None, None, None)
                except Exception:
                    pass
            elif self.config.transport == "stdio" and hasattr(self, '_stdio_context') and self._stdio_context:
                try:
                    await self._stdio_context.__aexit__(None, None, None)
                except Exception:
                    pass

            logger.info(f"[{self.name}] Disconnected")

        except Exception as e:
            logger.debug(f"[{self.name}] Disconnect cleanup: {e}")
        finally:
            self._session_context = None
            self._sse_context = None
            self._stdio_context = None
