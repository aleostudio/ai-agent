from typing import TypedDict, Optional

class AgentState(TypedDict):
    prompt: str
    response: Optional[str]
