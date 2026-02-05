from typing import TypedDict, Optional, Annotated
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph.message import add_messages


class SimpleAgentState(TypedDict):
    """State per l'agent con supporto tool calling."""
    
    # Input utente
    prompt: str
    
    # Messaggi conversazione (accumula con add_messages)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Output finale
    ai_message: Optional[AIMessage]
    generated_text: Optional[str]
    
    # Tool execution tracking
    tool_calls_count: int
