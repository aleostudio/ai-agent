import json
from typing import Literal, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.logger import logger
from app.model.simple_agent_state import SimpleAgentState
import app.prompts as prompts


# Agent with optional MCP tool calling
class SimpleAgent:

    def __init__(self, model: BaseChatModel, mcp_manager=None, system_prompt: str | None = None):
        self.base_model = model
        self.mcp_manager = mcp_manager
        self.tools_enabled = self._has_tools()
        
        # Get incoming system prompt if provided, otherwise choose right system prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = prompts.SYSTEM_PROMPT_TOOLS.format() if self.tools_enabled else prompts.SYSTEM_PROMPT.format()
        
        # Bind tools if enabled
        self.model = self._bind_tools(model) if self.tools_enabled else model
        
        # Build workflow
        self.workflow = self._build_workflow()
        self.graph = self.workflow.compile()


    # Check if there are tools available
    def _has_tools(self) -> bool:
        return (
            self.mcp_manager is not None 
            and self.mcp_manager.is_initialized 
            and len(self.mcp_manager.get_langchain_tools()) > 0
        )


    # Bind tools to the model
    def _bind_tools(self, model: BaseChatModel) -> BaseChatModel:
        tools = self.mcp_manager.get_langchain_tools()
        logger.info(f"Binding {len(tools)} tools to model: {[t.name for t in tools]}")
        return model.bind_tools(tools)


    # LangGraph workflow builder
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(SimpleAgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.set_entry_point("agent")

        if self.tools_enabled:
            # With tools
            workflow.add_node("tools", self._tools_node)
            workflow.add_conditional_edges("agent", self._should_continue, {"continue": "tools", "end": END})
            workflow.add_edge("tools", "agent")
        else:
            # Without tools -> directly to END
            workflow.add_edge("agent", END)

        return workflow


    # Path decision: decide to continue with tool execution or stop
    def _should_continue(self, state: SimpleAgentState) -> Literal["continue", "end"]:
        last_message = state["messages"][-1] if state["messages"] else None

        if state.get("tool_calls_count", 0) >= settings.MCP_TOOL_CALL_MAX_ITERATIONS:
            logger.warning("Max tool call iterations reached")
            return "end"

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        return "end"


    # Agent: LLM call
    def _agent_node(self, state: SimpleAgentState) -> dict:
        messages = state.get("messages", [])
        if not messages:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=state["prompt"])
            ]

        response = self.model.invoke(messages)

        # Log to understand if LLM has decided to call a tool
        if self.tools_enabled and response.tool_calls:
            logger.info(f"LLM calling {len(response.tool_calls)} tool(s): {[tc['name'] for tc in response.tool_calls]}")

        return {
            "messages": [response],
            "ai_message": response,
            "generated_text": response.content if not response.tool_calls else None
        }


    # Call tools requested by LLM
    async def _tools_node(self, state: SimpleAgentState) -> dict:
        last_message = state["messages"][-1]
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = await self._execute_tool_calls(last_message.tool_calls)

        return {
            "messages": tool_messages,
            "tool_calls_count": state.get("tool_calls_count", 0) + len(tool_messages)
        }


    # Execute tool calls and return ToolMessages
    async def _execute_tool_calls(self, tool_calls: list) -> list[ToolMessage]:
        tool_messages = []
        for tool_call in tool_calls:
            result_str = await self._call_single_tool(tool_call)
            tool_messages.append(ToolMessage(content=result_str, tool_call_id=tool_call["id"]))

        return tool_messages


    # Execute a single tool and return serialized result
    async def _call_single_tool(self, tool_call: dict) -> str:
        tool_name = tool_call["name"]
        tool_args = self._sanitize_tool_args(tool_call["args"])
        logger.info(f"Executing tool: {tool_name}")

        try:
            result = await self.mcp_manager.call_tool(tool_name, tool_args)
            logger.info(f"Tool {tool_name} completed")

            return self._serialize_result(result)

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")

            return json.dumps({"success": False, "error": str(e), "tool": tool_name})


    # Sanitize tool arguments
    def _sanitize_tool_args(self, args: dict) -> dict:
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


    # Serialize tool result
    def _serialize_result(self, result) -> str:
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return result
        
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        return str(result) if result is not None else "Success"


    # Interact with agent (sync)
    def interact(self, prompt: str) -> dict:
        output = self.graph.invoke({
            "prompt": prompt,
            "messages": [],
            "ai_message": None,
            "generated_text": None,
            "tool_calls_count": 0
        })

        return {"agent_response": output}


    # Interact with agent (async)
    async def async_interact(self, prompt: str) -> dict:
        output = await self.graph.ainvoke({
            "prompt": prompt,
            "messages": [],
            "ai_message": None,
            "generated_text": None,
            "tool_calls_count": 0
        })

        return {"agent_response": output}


    # Interact with agent (streaming tokens)
    async def stream_interact(self, prompt: str) -> AsyncIterator[str]:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        
        if self.tools_enabled:
            async for chunk in self._stream_with_tools(messages):
                yield chunk
        else:
            async for chunk in self._stream_direct(messages):
                yield chunk


    # Stream direct response without tools
    async def _stream_direct(self, messages: list) -> AsyncIterator[str]:
        async for chunk in self.base_model.astream(messages):
            if chunk.content:
                payload = {
                    "choices": [{
                        "delta": {"content": chunk.content},
                        "index": 0
                    }]
                }
                yield f"data: {json.dumps(payload)}\n\n"
        yield "data: [DONE]\n\n"


    # Stream with ReAct loop for tools
    async def _stream_with_tools(self, messages: list) -> AsyncIterator[str]:
        state = {"messages": messages, "tool_calls_count": 0}
        
        while state["tool_calls_count"] < settings.MCP_TOOL_CALL_MAX_ITERATIONS:
            response = self.model.invoke(state["messages"])
            state["messages"].append(response)
            
            if not response.tool_calls:
                async for chunk in self._stream_direct(state["messages"][:-1]):
                    yield chunk
                return
            
            tool_messages = await self._execute_tool_calls(response.tool_calls)
            state["messages"].extend(tool_messages)
            state["tool_calls_count"] += 1
        
        yield "data: [MAX_ITERATIONS]\n\n"


    # Get available tools name
    def get_tool_names(self) -> list[str]:
        if not self.tools_enabled:
            return []

        return [t.name for t in self.mcp_manager.get_langchain_tools()]
