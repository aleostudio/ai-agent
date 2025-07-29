from typing import TypedDict, Optional, List, Dict
from langchain.schema import AIMessage

class SimpleAgentState(TypedDict):
    prompt: str
    user_id: str
    ai_message: Optional[AIMessage]
    generated_text: Optional[str]
    memory: List[Dict[str, str]]