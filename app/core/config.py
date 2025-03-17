import os
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

class Settings:

    # App config
    APP_NAME: str = os.getenv("APP_NAME", "Simple AI agent")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 9201))
    API_VERSION: str = os.getenv("API_VERSION", "v1")

    # Logging
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # LLM config
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL: str = os.getenv("MODEL", "llama3.2")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.8))

settings = Settings()
