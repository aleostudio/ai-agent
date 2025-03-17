from pydantic import BaseModel
from app.core.config import settings
from typing import Optional

class SimpleAgentRequest(BaseModel):
    prompt: Optional[str] = ""
    model: Optional[str] = settings.MODEL
    temperature: Optional[float] = settings.TEMPERATURE
    
