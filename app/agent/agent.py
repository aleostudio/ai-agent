import json
import re
from typing import AsyncIterator, Callable, Literal
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from app.core.tool_runtime import AgentToolRuntime
from app.core.config import settings
from app.core.logger import logger
from app.agent.agent_state import AgentState
import app.prompts as prompts


# Agent focused on LangGraph workflow and interaction methods
class Agent:

    # Initialize the agent with model, tools runtime, and workflow customization hook
    def __init__(self, model: BaseChatModel, mcp_manager=None, system_prompt: str | None = None, extra_tools: list[BaseTool] | None = None, workflow_customizer: Callable[[StateGraph], None] | None = None):
        self.base_model = model
        self.tool_runtime = AgentToolRuntime(mcp_manager=mcp_manager, extra_tools=extra_tools)
        self.tools_enabled = self.tool_runtime.has_tools

        if system_prompt:
            self.system_prompt = system_prompt
        else:
            tool_names = self.tool_runtime.get_tool_names() if self.tools_enabled else None
            self.system_prompt = prompts.build_system_prompt("chat", tool_names=tool_names)

        self.model = self.tool_runtime.bind_model(model) if self.tools_enabled else model
        self.workflow = self._build_workflow(workflow_customizer)
        self.graph = self.workflow.compile()


    # Expose extra tools for API/introspection consumers
    @property
    def extra_tools(self) -> list[BaseTool]:
        return self.tool_runtime.extra_tools


    # Build the LangGraph workflow
    def _build_workflow(self, workflow_customizer: Callable[[StateGraph], None] | None) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.set_entry_point("agent")

        if self.tools_enabled:
            workflow.add_node("tools", self._tools_node)
            workflow.add_conditional_edges("agent", self._should_continue, {"continue": "tools", "end": END})
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)

        if workflow_customizer is not None:
            workflow_customizer(workflow)

        return workflow


    # Decide whether to continue into tool execution or terminate the graph
    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        last_message = state["messages"][-1] if state["messages"] else None

        if state.get("tool_calls_count", 0) >= settings.TOOL_CALL_MAX_ITERATIONS:
            logger.warning("Max tool call iterations reached")
            return "end"

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        return "end"


    # Run the model node and return agent output state payload
    async def _agent_node(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        if not messages:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=state["prompt"]),
            ]

        response = await self.model.ainvoke(messages)

        if self.tools_enabled and response.tool_calls:
            logger.info("LLM calling %s tool(s): %s", len(response.tool_calls), [tc["name"] for tc in response.tool_calls])

        content = self._content_to_text(response.content) if not response.tool_calls else None
        if content and self.tools_enabled:
            content = self._clean_tool_leaks(content)
            response.content = content

        return {
            "messages": [response], 
            "ai_message": response, 
            "generated_text": content
        }


    # Execute tool calls requested by the last AI message
    async def _tools_node(self, state: AgentState) -> dict:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = await self.tool_runtime.execute_tool_calls(last_message.tool_calls)

        return {
            "messages": tool_messages,
            "tool_calls_count": state.get("tool_calls_count", 0) + 1,
        }


    # Build the initial graph state for a new interaction
    def _initial_state(self, prompt: str) -> dict:
        return {
            "prompt": prompt,
            "messages": [],
            "ai_message": None,
            "generated_text": None,
            "tool_calls_count": 0,
        }


    # Run a synchronous graph interaction
    def interact(self, prompt: str) -> dict:
        output = self.graph.invoke(self._initial_state(prompt))
        return {"agent_response": output}


    # Run an asynchronous graph interaction
    async def async_interact(self, prompt: str) -> dict:
        output = await self.graph.ainvoke(self._initial_state(prompt))
        return {"agent_response": output}


    # Stream interaction output, with or without tool execution loop
    async def stream_interact(self, prompt: str) -> AsyncIterator[str]:
        messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)]

        if self.tools_enabled:
            async for chunk in self._stream_with_tools(messages):
                yield chunk
        else:
            async for chunk in self._stream_direct(messages):
                yield chunk


    # Stream direct model output when no tool loop is needed
    async def _stream_direct(self, messages: list) -> AsyncIterator[str]:
        async for chunk in self.base_model.astream(messages):
            text = self._content_to_text(chunk.content)
            if text:
                payload = {"choices": [{"delta": {"content": text}, "index": 0}]}
                yield f"data: {json.dumps(payload)}\n\n"
        yield "data: [DONE]\n\n"


    # Stream output while iterating model/tool steps until completion
    async def _stream_with_tools(self, messages: list) -> AsyncIterator[str]:
        state = {"messages": messages, "tool_calls_count": 0}

        while state["tool_calls_count"] < settings.TOOL_CALL_MAX_ITERATIONS:
            response = await self.model.ainvoke(state["messages"])
            state["messages"].append(response)

            if not response.tool_calls:
                final_text = self._content_to_text(response.content)
                if final_text:
                    final_text = self._clean_tool_leaks(final_text)
                    payload = {"choices": [{"delta": {"content": final_text}, "index": 0}]}
                    yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"
                return

            tool_messages = await self.tool_runtime.execute_tool_calls(response.tool_calls)
            state["messages"].extend(tool_messages)
            state["tool_calls_count"] += 1

        yield "data: [MAX_ITERATIONS]\n\n"


    # Normalize message content to plain text
    def _content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)

            return "\n".join(parts)

        return str(content or "")


    # Remove leaked tool-call syntax from model text output
    def _clean_tool_leaks(self, text: str) -> str:
        if not text:
            return text

        cleaned = re.sub(r'\{["\']name["\']:\s*["\'][\w-]+["\'].*?\}(?:\s*\})?', "", text, flags=re.DOTALL)

        tool_patterns = [
            r"(?i)[^\n.]*\b(?:function|tool)\s+(?:call|invocation|name)[^\n.]*[.\n]?",
            r"(?i)[^\n.]*\bmcp-server__\w+[^\n.]*[.\n]?",
            r"(?i)[^\n.]*\bI (?:don't have|cannot find|lack) (?:a |the )?(?:specific |direct )?(?:function|tool)[^\n.]*[.\n]?",
            r"(?i)[^\n.]*\bI'll (?:suggest|attempt|try) (?:to )?(?:call|use|invoke)[^\n.]*[.\n]?",
            r"(?i)[^\n.]*\bHere's the JSON[^\n.]*[.\n]?",
            r"(?i)[^\n.]*\bprovided functions?\b[^\n.]*[.\n]?",
        ]

        for pattern in tool_patterns:
            cleaned = re.sub(pattern, "", cleaned)

        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if cleaned != text:
            logger.debug("Cleaned tool leak from model response")

        return cleaned
