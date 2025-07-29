from pydantic import BaseModel
from typing import Optional

class SimpleAgentRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = None