from typing import TypedDict, Optional, Annotated
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph.message import add_messages

# Agent state with tools calling support
class SimpleAgentState(TypedDict):

    # User input
    prompt: str
    
    # Conversation messages (accumulate through add_messages)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Final output
    ai_message: Optional[AIMessage]
    generated_text: Optional[str]
    
    # Tool execution tracking
    tool_calls_count: int
