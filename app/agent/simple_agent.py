"""
SimpleAgent con supporto MCP tools.
Implementa un ReAct loop: LLM decide se usare tools, esegue, e continua fino a risposta finale.
"""
import json
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.logger import logger
from app.model.simple_agent_state import SimpleAgentState
from app.mcp import MCPToolManager


# System prompt per guidare l'uso dei tool
SYSTEM_PROMPT = """You are a helpful assistant with access to external tools.

Available tools can help you with:
- Mathematical calculations (calculate)
- Date and time information (get_datetime)  
- Text processing and analysis (process_text): word_count, char_count, reverse, uppercase, lowercase, title_case, extract_emails, extract_urls, summarize_stats
- Fetching web content (fetch_url)
- Data format conversion (convert_data): json, base64, hex

Guidelines:
- Use tools ONLY when the task requires computation, data processing, or external information
- For general conversation, jokes, explanations, or creative writing, respond directly WITHOUT using tools
- When a tool returns a result, interpret it and provide a clear, human-friendly answer to the user
- Always respond in the same language as the user's question
- If a tool returns an error, explain the issue clearly and try to help the user anyway
"""


class SimpleAgent:
    """
    Agent con supporto tool calling via MCP.
    
    Workflow:
    1. Riceve prompt utente
    2. LLM decide se rispondere o usare tools
    3. Se tool call → esegue tool → torna a LLM con risultato
    4. Loop fino a risposta finale (no tool calls)
    """

    def __init__(
        self, 
        model: BaseChatModel, 
        mcp_manager: MCPToolManager | None = None,
        system_prompt: str | None = None
    ):
        self.base_model = model
        self.mcp_manager = mcp_manager
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.model = self._bind_tools(model)
        self.workflow = self._build_workflow()
        self.graph = self.workflow.compile()

    def _bind_tools(self, model: BaseChatModel) -> BaseChatModel:
        """Bind MCP tools al modello se disponibili."""
        if not self.mcp_manager or not self.mcp_manager.is_initialized:
            logger.info("No MCP tools available, running without tools")
            return model

        tools = self.mcp_manager.get_langchain_tools()
        if not tools:
            logger.info("No tools found from MCP servers")
            return model

        logger.info(f"Binding {len(tools)} tools to model: {[t.name for t in tools]}")
        return model.bind_tools(tools)

    def _build_workflow(self) -> StateGraph:
        """Costruisce il workflow LangGraph con ReAct loop."""
        workflow = StateGraph(SimpleAgentState)

        # Nodi
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)

        # Entry point
        workflow.set_entry_point("agent")

        # Conditional edge: se ci sono tool calls → tools, altrimenti → END
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )

        # Dopo tools, torna sempre all'agent
        workflow.add_edge("tools", "agent")

        return workflow

    def _should_continue(self, state: SimpleAgentState) -> Literal["continue", "end"]:
        """Decide se continuare con tool execution o terminare."""
        last_message = state["messages"][-1] if state["messages"] else None

        # Check max iterations
        if state.get("tool_calls_count", 0) >= settings.MCP_TOOL_CALL_MAX_ITERATIONS:
            logger.warning("Max tool call iterations reached")
            return "end"

        # Se l'ultimo messaggio ha tool_calls, continua
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "continue"

        return "end"

    def _agent_node(self, state: SimpleAgentState) -> dict:
        """Nodo agent: chiama LLM."""
        messages = state.get("messages", [])
        
        # Prima invocazione: aggiungi system prompt + user prompt
        if not messages:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=state["prompt"])
            ]

        # Invoca LLM
        response = self.model.invoke(messages)
        
        # Log della decisione
        if response.tool_calls:
            logger.info(f"LLM decided to call {len(response.tool_calls)} tool(s): {[tc['name'] for tc in response.tool_calls]}")
        else:
            logger.info("LLM responding directly without tools")

        return {
            "messages": [response],
            "ai_message": response,
            "generated_text": response.content if not response.tool_calls else None
        }

    async def _tools_node(self, state: SimpleAgentState) -> dict:
        """Nodo tools: esegue i tool richiesti dall'LLM."""
        last_message = state["messages"][-1]
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            # Sanitizza argomenti (es. options vuoto)
            tool_args = self._sanitize_tool_args(tool_args)

            logger.info(f"Executing tool: {tool_name}")
            logger.debug(f"Tool args: {tool_args}")

            try:
                result = await self.mcp_manager.call_tool(tool_name, tool_args)
                
                # Parse risultato se è stringa JSON
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        pass  # Mantieni come stringa
                
                # Serializza per il messaggio
                if isinstance(result, (dict, list)):
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(result) if result is not None else "Success"

                logger.info(f"Tool {tool_name} completed successfully")
                logger.debug(f"Tool result: {result_str[:500]}...")

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                result_str = json.dumps({
                    "success": False, 
                    "error": str(e),
                    "tool": tool_name
                })

            tool_messages.append(
                ToolMessage(content=result_str, tool_call_id=tool_id)
            )

        return {
            "messages": tool_messages,
            "tool_calls_count": state.get("tool_calls_count", 0) + len(tool_messages)
        }

    def _sanitize_tool_args(self, args: dict) -> dict:
        """
        Sanitizza gli argomenti dei tool.
        Gestisce casi comuni come stringhe vuote al posto di None/dict.
        """
        sanitized = {}
        for key, value in args.items():
            # Stringa vuota → None (il tool deciderà il default)
            if value == "":
                sanitized[key] = None
            # Stringa "null" o "none" → None
            elif isinstance(value, str) and value.lower() in ("null", "none"):
                sanitized[key] = None
            # Stringa JSON → parse
            elif isinstance(value, str) and value.startswith(("{", "[")):
                try:
                    sanitized[key] = json.loads(value)
                except json.JSONDecodeError:
                    sanitized[key] = value
            else:
                sanitized[key] = value
        
        return sanitized

    def interact(self, prompt: str) -> dict:
        """
        Esegue l'agent con il prompt dato (sincrono).
        
        Args:
            prompt: Input utente
            
        Returns:
            Dict con agent_response contenente ai_message e generated_text
        """
        initial_state = {
            "prompt": prompt,
            "messages": [],
            "ai_message": None,
            "generated_text": None,
            "tool_calls_count": 0
        }

        output = self.graph.invoke(initial_state)

        return {"agent_response": output}

    async def ainteract(self, prompt: str) -> dict:
        """
        Esegue l'agent con il prompt dato (asincrono).
        
        Args:
            prompt: Input utente
            
        Returns:
            Dict con agent_response contenente ai_message e generated_text
        """
        initial_state = {
            "prompt": prompt,
            "messages": [],
            "ai_message": None,
            "generated_text": None,
            "tool_calls_count": 0
        }

        output = await self.graph.ainvoke(initial_state)

        return {"agent_response": output}

    def get_tool_names(self) -> list[str]:
        """Restituisce i nomi dei tool disponibili."""
        if not self.mcp_manager or not self.mcp_manager.is_initialized:
            return []
        return [t.name for t in self.mcp_manager.get_langchain_tools()]