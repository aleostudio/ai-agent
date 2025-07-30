from fastapi import FastAPI, HTTPException
from app.core.config import settings
from app.core.logger import logger
from app.agent.simple_agent import SimpleAgent
from app.memory.short_term_memory_manager import ShortTermMemoryManager
from app.memory.long_term_memory_manager import LongTermMemoryManager
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
simple_agent = SimpleAgent(model, ShortTermMemoryManager(), LongTermMemoryManager())


# API exposition
@app.post("/interact")
async def interact(request: SimpleAgentRequest):
    try:
        response_type = "ai_message"
        if settings.RESPONSE_TYPE == "text":
            response_type = "generated_text"

        # Interact with agent
        response = simple_agent.interact(request.prompt, request.user_id)
        return {"user_id": response['user_id'], "response": response['agent_response'][response_type]}

    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))


# Active users with existing memory
@app.get("/memory")
async def get_active_users():
    try:
        users = simple_agent.short_memory.get_all_users()
        return {"total_users": len(users), "active_users": users}

    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        raise HTTPException(status_code = 500, detail = str(e))


# Get memory for given user
@app.get("/memory/{user_id}")
async def get_user_memory(user_id: str):
    try:
        return simple_agent.short_memory.get_messages(user_id)

    except Exception as e:
        logger.error(f"Error getting memory for user {user_id}: {e}")
        raise HTTPException(status_code = 500, detail = str(e))


# Clear memory for given user
@app.delete("/memory/{user_id}")
async def clear_user_memory(user_id: str):
    try:
        success = simple_agent.short_memory.clear_user(user_id)
        if success:
            return {"message": f"Memory erased for user {user_id}"}
        else:
            return {"message": f"No memory found for user {user_id}"}

    except Exception as e:
        logger.error(f"Error clearing memory for user {user_id}: {e}")
        raise HTTPException(status_code = 500, detail = str(e))


# Health check API
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Service is running"}
