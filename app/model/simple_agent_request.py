from pydantic import BaseModel
from typing import Optional

class SimpleAgentRequest(BaseModel):
    prompt: Optional[str] = ""
    
