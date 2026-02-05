"""
MCP Tool Manager - Gestisce connessioni a più server MCP e converte i tool in formato LangChain.
"""
import asyncio
import json
import logging
from typing import Any, Callable
from dataclasses import dataclass

from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, create_model

from app.mcp.client import MCPClient, MCPServerConfig

logger = logging.getLogger(__name__)


def _json_schema_to_pydantic_field(name: str, schema: dict[str, Any]) -> tuple[type, Any]:
    """Converte un JSON schema field in un tipo Pydantic."""
    json_type = schema.get("type", "string")
    description = schema.get("description", "")
    default = schema.get("default", ...)

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    python_type = type_mapping.get(json_type, str)
    
    # Gestione tipi nullable
    if "null" in schema.get("type", []) if isinstance(schema.get("type"), list) else False:
        python_type = python_type | None

    return (python_type, Field(default=default, description=description))


def _create_tool_input_model(tool_name: str, input_schema: dict[str, Any]) -> type[BaseModel]:
    """Crea dinamicamente un Pydantic model dagli input schema del tool MCP."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields = {}
    for prop_name, prop_schema in properties.items():
        python_type, field_info = _json_schema_to_pydantic_field(prop_name, prop_schema)
        
        # Se non è required, il default è None
        if prop_name not in required and field_info.default is ...:
            field_info = Field(default=None, description=field_info.description)
            python_type = python_type | None

        fields[prop_name] = (python_type, field_info)

    model_name = f"{tool_name.replace('-', '_').title()}Input"
    return create_model(model_name, **fields)


class MCPLangChainTool(BaseTool):
    """Wrapper LangChain per un tool MCP."""
    
    name: str
    description: str
    args_schema: type[BaseModel]
    mcp_client: MCPClient
    mcp_tool_name: str

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **kwargs: Any) -> str:
        """Esecuzione sincrona (wrapper async)."""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> str:
        """Esecuzione asincrona del tool MCP."""
        try:
            result = await self.mcp_client.call_tool(self.mcp_tool_name, kwargs)
            
            # Serializza risultato se necessario
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result) if result is not None else "Tool executed successfully"
            
        except Exception as e:
            logger.error(f"Tool '{self.name}' execution failed: {e}")
            raise ToolException(f"Tool execution failed: {e}")


class MCPToolManager:
    """
    Gestisce più server MCP e fornisce i tool in formato LangChain.
    
    Usage:
        manager = MCPToolManager(configs)
        await manager.connect_all()
        tools = manager.get_langchain_tools()
        # ... usa i tools con LangChain/LangGraph
        await manager.disconnect_all()
    """

    def __init__(self, configs: list[MCPServerConfig]):
        self.configs = [c for c in configs if c.enabled]
        self.clients: dict[str, MCPClient] = {}
        self._langchain_tools: list[BaseTool] = []
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def connected_servers(self) -> list[str]:
        return [name for name, client in self.clients.items() if client.is_connected]

    async def connect_all(self) -> None:
        """Connette a tutti i server MCP configurati."""
        if self._initialized:
            logger.warning("MCPToolManager already initialized")
            return

        logger.info(f"Connecting to {len(self.configs)} MCP servers...")

        for config in self.configs:
            try:
                client = MCPClient(config)
                await client.connect()
                self.clients[config.name] = client
            except Exception as e:
                logger.error(f"Failed to connect to '{config.name}': {e}")
                # Continua con gli altri server

        # Costruisci i LangChain tools
        self._build_langchain_tools()
        self._initialized = True

        logger.info(
            f"MCPToolManager initialized: {len(self.clients)} servers, "
            f"{len(self._langchain_tools)} tools available"
        )

    def _build_langchain_tools(self) -> None:
        """Converte tutti i tool MCP in LangChain tools."""
        self._langchain_tools = []

        for server_name, client in self.clients.items():
            for mcp_tool in client.tools:
                try:
                    # Crea input model dinamico
                    input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}
                    args_model = _create_tool_input_model(mcp_tool.name, input_schema)

                    # Nome tool prefissato con server per evitare collisioni
                    tool_name = f"{server_name}__{mcp_tool.name}"

                    lc_tool = MCPLangChainTool(
                        name=tool_name,
                        description=mcp_tool.description or f"Tool {mcp_tool.name} from {server_name}",
                        args_schema=args_model,
                        mcp_client=client,
                        mcp_tool_name=mcp_tool.name,
                    )
                    self._langchain_tools.append(lc_tool)

                    logger.debug(f"Registered tool: {tool_name}")

                except Exception as e:
                    logger.error(f"Failed to convert tool '{mcp_tool.name}': {e}")

    def get_langchain_tools(self) -> list[BaseTool]:
        """Restituisce tutti i tool in formato LangChain."""
        if not self._initialized:
            raise RuntimeError("MCPToolManager not initialized. Call connect_all() first.")
        return self._langchain_tools

    def get_tools_by_server(self, server_name: str) -> list[BaseTool]:
        """Restituisce i tool di un server specifico."""
        prefix = f"{server_name}__"
        return [t for t in self._langchain_tools if t.name.startswith(prefix)]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Chiama un tool dato il nome completo (server__tool_name).
        Tenta riconnessione automatica se il server è disconnesso.
        """
        if "__" not in tool_name:
            raise ValueError(f"Tool name deve essere nel formato 'server__tool': {tool_name}")

        server_name, mcp_tool_name = tool_name.split("__", 1)

        if server_name not in self.clients:
            raise ValueError(f"Server '{server_name}' not found")

        client = self.clients[server_name]
        
        # Tenta riconnessione se disconnesso
        if not client.is_connected:
            logger.info(f"Server '{server_name}' disconnected, attempting reconnect...")
            try:
                await client.connect()
                logger.info(f"Reconnected to '{server_name}'")
            except Exception as e:
                logger.error(f"Reconnect to '{server_name}' failed: {e}")
                raise RuntimeError(f"Server '{server_name}' unavailable: {e}")

        return await client.call_tool(mcp_tool_name, arguments)

    async def disconnect_all(self) -> None:
        """Disconnette da tutti i server MCP."""
        for client in self.clients.values():
            await client.disconnect()
        
        self.clients.clear()
        self._langchain_tools.clear()
        self._initialized = False
        logger.info("MCPToolManager disconnected from all servers")

    async def __aenter__(self):
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_all()
