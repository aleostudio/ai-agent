from fastapi import FastAPI, HTTPException
from app.core.config import settings
from app.core.logger import logger
from app.core.provider import get_model_from_provider
from app.agent.agent import Agent
from app.model.agent_request import AgentRequest
import traceback


# App and LLM model init
app = FastAPI(title = settings.APP_NAME, version = settings.API_VERSION)
model = get_model_from_provider()

# Init agent
agent = Agent(model)

# API exposition
@app.post("/interact")
async def interact(request: AgentRequest):
    try:
        agent_response = agent.interact(request.prompt)

        logger.info("Input prompt: " + agent_response["agent_response"]["prompt"])
        logger.info("Model response: " + agent_response["agent_response"]["response"])
        logger.info("=========================================================")

        return {
            "response": agent_response['agent_response']["response"],
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code = 500, detail = str(e))

# Health check API
@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "message": "Service is running"
    }
