import asyncio
import json
import logging
from typing import Any
from langchain_core.tools import BaseTool, ToolException
from pydantic import ConfigDict, BaseModel, Field, create_model
from app.mcp.client import MCPClient, MCPServerConfig

# Global logger
logger = logging.getLogger(__name__)


# Convert a JSON schema field to Pydantic type
def _json_schema_to_pydantic_field(_name: str, schema: dict[str, Any]) -> tuple[type, Any]:
    json_type = schema.get("type", "string")
    description = schema.get("description", "")
    default = schema.get("default", ...)
    type_mapping = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}
    python_type = type_mapping.get(json_type, str)
    if "null" in schema.get("type", []) if isinstance(schema.get("type"), list) else False:
        python_type = python_type | None

    return (python_type, Field(default=default, description=description))


# Create dynamically a Pydantic model from MCP tool input schema
def _create_tool_input_model(tool_name: str, input_schema: dict[str, Any]) -> type[BaseModel]:
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    fields = {}
    for prop_name, prop_schema in properties.items():
        python_type, field_info = _json_schema_to_pydantic_field(prop_name, prop_schema)
        if prop_name not in required and field_info.default is ...:
            field_info = Field(default=None, description=field_info.description)
            python_type = python_type | None

        fields[prop_name] = (python_type, field_info)

    model_name = f"{tool_name.replace('-', '_').title()}Input"

    return create_model(model_name, **fields)


# LangChain wrapper for MCP tool
class MCPLangChainTool(BaseTool):    
    name: str
    description: str
    args_schema: type[BaseModel]
    mcp_client: MCPClient
    mcp_tool_name: str
    model_config = ConfigDict(arbitrary_types_allowed=True)


    # Async wrapper
    def _run(self, **kwargs: Any) -> str:
        return asyncio.run(self._arun(**kwargs))


    # Async MCP tool execution
    async def _arun(self, **kwargs: Any) -> str:
        try:
            result = await self.mcp_client.call_tool(self.mcp_tool_name, kwargs)

            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result) if result is not None else "Tool executed successfully"
            
        except Exception as e:
            logger.error(f"Tool '{self.name}' execution failed: {e}")
            raise ToolException(f"Tool execution failed: {e}")


# Handle multiple MCP servers and convert tools in LangChain format
class MCPToolManager:

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


    # Connect to all configured MCP servers
    async def connect_all(self) -> None:
        if self._initialized:
            return

        for config in self.configs:
            try:
                client = MCPClient(config)
                await client.connect()
                self.clients[config.name] = client
            except Exception as e:
                logger.error(f"Failed to connect to '{config.name}': {e}")

        self._build_langchain_tools()
        self._initialized = True

        logger.info(f"MCP manager initialized: {len(self.clients)} servers, {len(self._langchain_tools)} tools available")


    # Convert MCP tools in LangChain tools
    def _build_langchain_tools(self) -> None:
        self._langchain_tools = []

        for server_name, client in self.clients.items():
            for mcp_tool in client.tools:
                try:
                    input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}
                    args_model = _create_tool_input_model(mcp_tool.name, input_schema)

                    # Add server as prefix to the tool name to avoid collisions
                    tool_name = f"{server_name}__{mcp_tool.name}"

                    lc_tool = MCPLangChainTool(
                        name=tool_name,
                        description=mcp_tool.description or f"Tool {mcp_tool.name} from {server_name}",
                        args_schema=args_model,
                        mcp_client=client,
                        mcp_tool_name=mcp_tool.name,
                    )
                    self._langchain_tools.append(lc_tool)

                except Exception as e:
                    logger.error(f"Failed to convert tool '{mcp_tool.name}': {e}")


    # Get all tools in LangChain format
    def get_langchain_tools(self) -> list[BaseTool]:
        if not self._initialized:
            raise RuntimeError("MCP manager not initialized. Call connect_all() first.")
        return self._langchain_tools


    # Get all tools of specific server
    def get_tools_by_server(self, server_name: str) -> list[BaseTool]:
        prefix = f"{server_name}__"
        return [t for t in self._langchain_tools if t.name.startswith(prefix)]


    # Call remote tool by name
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if "__" not in tool_name:
            raise ValueError(f"Tool name format must be 'server__tool': {tool_name}")

        server_name, mcp_tool_name = tool_name.split("__", 1)
        if server_name not in self.clients:
            raise ValueError(f"Server '{server_name}' not found")

        client = self.clients[server_name]
        
        # Handle server reconnection if the server results disconnected
        if not client.is_connected:
            logger.info(f"Server '{server_name}' disconnected, attempting reconnect")
            try:
                await client.connect()
                logger.info(f"Reconnected to '{server_name}'")
            except Exception as e:
                logger.error(f"Reconnect to '{server_name}' failed: {e}")
                raise RuntimeError(f"Server '{server_name}' unavailable: {e}")

        return await client.call_tool(mcp_tool_name, arguments)


    # Disconnect from all MCP servers
    async def disconnect_all(self) -> None:
        for client in self.clients.values():
            await client.disconnect()
        
        self.clients.clear()
        self._langchain_tools.clear()
        self._initialized = False
        logger.info("MCP manager disconnected from all servers")


    # Connect all alias
    async def __aenter__(self):
        await self.connect_all()
        return self


    # Disconnect all alias
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_all()
