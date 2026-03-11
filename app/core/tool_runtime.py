import asyncio
import json
from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from app.core.logger import logger


# Owns tool binding and execution for the agent runtime
class AgentToolRuntime:

    # Initialize runtime references for MCP and additional tools
    def __init__(self, mcp_manager=None, extra_tools: list[BaseTool] | None = None):
        self.mcp_manager = mcp_manager
        self.extra_tools = extra_tools or []
        self.extra_tools_map = {t.name: t for t in self.extra_tools}


    # Check if at least one tool source is available
    @property
    def has_tools(self) -> bool:
        has_mcp = (self.mcp_manager is not None and self.mcp_manager.is_initialized and len(self.mcp_manager.get_langchain_tools()) > 0)

        return has_mcp or len(self.extra_tools) > 0


    # Bind all available tools to the chat model
    def bind_model(self, model: BaseChatModel) -> BaseChatModel:
        tools: list[BaseTool] = []
        if self.mcp_manager and self.mcp_manager.is_initialized:
            tools.extend(self.mcp_manager.get_langchain_tools())
        tools.extend(self.extra_tools)
        logger.info("Binding %s tools to model: %s", len(tools), [t.name for t in tools])

        return model.bind_tools(tools)


    # Return the list of tool names exposed to the model
    def get_tool_names(self) -> list[str]:
        if not self.has_tools:
            return []
        names = []
        if self.mcp_manager and self.mcp_manager.is_initialized:
            names.extend(t.name for t in self.mcp_manager.get_langchain_tools())
        names.extend(t.name for t in self.extra_tools)

        return names


    # Execute multiple tool calls and convert outputs to ToolMessage
    async def execute_tool_calls(self, tool_calls: list[dict]) -> list[ToolMessage]:
        results = await asyncio.gather(*[self._call_single_tool(tc) for tc in tool_calls])

        return [
            ToolMessage(content=result_str, tool_call_id=tool_call["id"])
            for tool_call, result_str in zip(tool_calls, results)
        ]


    # Execute one tool call via extra tools or MCP manager
    async def _call_single_tool(self, tool_call: dict[str, Any]) -> str:
        tool_name = tool_call["name"]
        tool_args = self._sanitize_tool_args(tool_call.get("args"))
        logger.info("Executing tool: %s", tool_name)

        try:
            if tool_name in self.extra_tools_map:
                result = await self.extra_tools_map[tool_name].ainvoke(tool_args)
                logger.info("Tool %s completed", tool_name)
                return self._serialize_result(result)

            if not self.mcp_manager:
                raise ValueError(f"Unknown tool: {tool_name}")

            result = await self.mcp_manager.call_tool(tool_name, tool_args)
            logger.info("Tool %s completed", tool_name)

            return self._serialize_result(result)

        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return json.dumps({"success": False, "error": str(e), "tool": tool_name})


    # Normalize tool arguments coming from model tool calls
    def _sanitize_tool_args(self, args: dict | None) -> dict:
        if args is None:
            return {}
        if not isinstance(args, dict):
            return {"input": args}

        sanitized = {}
        for key, value in args.items():
            if value == "" or (isinstance(value, str) and value.lower() in ("null", "none")):
                sanitized[key] = None
            elif isinstance(value, str) and value.startswith(("{", "[")):
                try:
                    sanitized[key] = json.loads(value)
                except json.JSONDecodeError:
                    sanitized[key] = value
            else:
                sanitized[key] = value

        return sanitized


    # Serialize tool outputs into stable string payloads
    def _serialize_result(self, result: Any) -> str:
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return result

        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)

        return str(result) if result is not None else "Success"
