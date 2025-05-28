from pydantic import BaseModel
from typing import Optional

class AgentRequest(BaseModel):
    prompt: Optional[str] = ""
