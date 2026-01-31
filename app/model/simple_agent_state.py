from typing import TypedDict, Optional
from langchain_core.messages import AIMessage

class SimpleAgentState(TypedDict):
    prompt: str
    ai_message: Optional[AIMessage]
    generated_text: Optional[str]
