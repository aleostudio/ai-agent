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

    # Model config
    PROVIDER: str = os.getenv("PROVIDER", "ollama")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama3.2")
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", 0.8))
    DEFAULT_SYSTEM_PROMPT: str = os.getenv("DEFAULT_SYSTEM_PROMPT", "You are an helpful assistant.")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    # OpenAi
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Claude
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Deepseek
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # Groq
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")


settings = Settings()
