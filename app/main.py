from fastapi import FastAPI, HTTPException
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.model.simple_agent_request import SimpleAgentRequest
from langchain_ollama import ChatOllama

# App and LLM model init
app = FastAPI(title = settings.APP_NAME, version = settings.API_VERSION)
model = ChatOllama(model = settings.MODEL, temperature = settings.TEMPERATURE, base_url = settings.OLLAMA_BASE_URL)

# Init agent
simple_agent = SimpleAgent(model)

# API exposition
@app.post("/interact")
async def interact(request: SimpleAgentRequest):
    try:
        response = simple_agent.interact(request.prompt)
        logger.info(response["agent_response"]["prompt"])

        return {
            "response": response['agent_response']["ai_message"],
        }

    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))

# Health check API
@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "message": "Service is running"
    }
