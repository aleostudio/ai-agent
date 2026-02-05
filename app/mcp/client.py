"""
MCP Client - Gestisce connessioni a server MCP via SSE o STDIO.
"""
import asyncio
import logging
from typing import Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configurazione per un singolo server MCP."""
    name: str
    transport: str  # "sse" | "stdio"
    url: str | None = None  # Per SSE
    command: str | None = None  # Per STDIO
    args: list[str] = field(default_factory=list)  # Per STDIO
    env: dict[str, str] | None = None  # Per STDIO
    timeout: float = 30.0
    enabled: bool = True

    def __post_init__(self):
        if self.transport == "sse" and not self.url:
            raise ValueError(f"Server '{self.name}': SSE transport richiede 'url'")
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"Server '{self.name}': STDIO transport richiede 'command'")


class MCPClient:
    """
    Client per comunicare con un server MCP.
    Supporta SSE e STDIO transport.
    """

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

    async def connect(self) -> None:
        """Stabilisce connessione al server MCP."""
        # Reset stato se era connesso prima
        if self._connected:
            await self.disconnect()

        try:
            if self.config.transport == "sse":
                await self._connect_sse()
            elif self.config.transport == "stdio":
                await self._connect_stdio()
            else:
                raise ValueError(f"Transport non supportato: {self.config.transport}")

            # Fetch available tools
            await self._load_tools()
            self._connected = True
            logger.info(f"[{self.name}] Connected, {len(self._tools)} tools available")

        except Exception as e:
            self._connected = False
            logger.error(f"[{self.name}] Connection failed: {e}")
            raise

    async def _connect_sse(self) -> None:
        """Connessione SSE."""
        self._sse_context = sse_client(url=self.config.url)
        streams = await self._sse_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()

    async def _connect_stdio(self) -> None:
        """Connessione STDIO."""
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env
        )
        self._stdio_context = stdio_client(server_params)
        streams = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()

    async def _load_tools(self) -> None:
        """Carica la lista dei tool disponibili."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        result = await self.session.list_tools()
        self._tools = result.tools
        logger.debug(f"[{self.name}] Loaded tools: {[t.name for t in self._tools]}")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Invoca un tool sul server MCP.
        """
        if not self.session:
            raise RuntimeError(f"[{self.name}] Not connected")

        logger.debug(f"[{self.name}] Calling tool '{tool_name}' with args: {arguments}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Estrai contenuto dalla risposta MCP
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
            # Connessione persa
            self._connected = False
            self.session = None
            logger.warning(f"[{self.name}] Connection lost: {e}")
            raise RuntimeError(f"MCP server '{self.name}' disconnected")


    async def disconnect(self) -> None:
        """Chiude la connessione."""
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