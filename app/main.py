from fastapi import FastAPI, HTTPException
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.model.simple_agent_request import SimpleAgentRequest
from langchain.chat_models import init_chat_model

# Avoid SSL verification
import truststore
truststore.inject_into_ssl()

# App and LLM model init
app = FastAPI(title = settings.APP_NAME, version = settings.API_VERSION)
model = init_chat_model(
    settings.MODEL, 
    model_provider = settings.PROVIDER, 
    base_url = settings.PROVIDER_BASE_URL,
    api_key = settings.PROVIDER_API_KEY,
    temperature = settings.TEMPERATURE,
    max_retries = settings.MAX_RETRIES
)

# Init agent
simple_agent = SimpleAgent(model)

# API exposition
@app.post("/interact")
async def interact(request: SimpleAgentRequest):
    try:
        response_type = "ai_message"
        if settings.RESPONSE_TYPE == "text":
            response_type = "generated_text"

        response = simple_agent.interact(request.prompt)
        logger.info(response["agent_response"]["prompt"])        
        
        return {"response": response['agent_response'][response_type]}

    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))

# Health check API
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Service is running"}
