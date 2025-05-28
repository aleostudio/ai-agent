import httpx
from app.core.config import settings
from typing import Callable, Any, TypedDict, Literal

class ChatMessage(TypedDict):
    role: Literal["user", "system", "assistant"]
    content: str

ChatModel = Callable[[list[ChatMessage]], Any]

def get_model_from_provider() -> ChatModel:

    match settings.PROVIDER:

        case "ollama":
            from openai import OpenAI
            client = OpenAI(base_url = settings.OLLAMA_BASE_URL, api_key = "-")
            return lambda messages: client.chat.completions.create(
                model = settings.DEFAULT_MODEL,
                messages = messages,
                temperature = settings.DEFAULT_TEMPERATURE,
            )

        case "openai":
            from openai import OpenAI
            client = OpenAI(base_url = settings.OPENAI_BASE_URL, api_key = settings.OPENAI_API_KEY)
            return lambda messages: client.chat.completions.create(
                model = settings.DEFAULT_MODEL,
                messages = messages,
                temperature = settings.DEFAULT_TEMPERATURE,
            )

        case "claude":
            import anthropic
            client = anthropic.Anthropic(api_key = settings.ANTHROPIC_API_KEY)
            def call_claude(messages):
                return client.messages.create(
                    model = settings.DEFAULT_MODEL,
                    max_tokens = 1024,
                    temperature = settings.DEFAULT_TEMPERATURE,
                    system = next((m["content"] for m in messages if m["role"] == "system"), None),
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in messages if m["role"] in {"user", "assistant"}
                    ]
                )
            return call_claude

        case "deepseek":
            from openai import OpenAI
            client = OpenAI(base_url = settings.DEEPSEEK_BASE_URL, api_key = settings.DEEPSEEK_API_KEY)
            return lambda messages: client.chat.completions.create(
                model = settings.DEFAULT_MODEL,
                messages = messages,
                temperature = settings.DEFAULT_TEMPERATURE,
            )

        case "groq":
            from openai import OpenAI
            client = OpenAI(base_url = settings.GROQ_BASE_URL, api_key = settings.GROQ_API_KEY, http_client=httpx.Client(verify=False))
            return lambda messages: client.chat.completions.create(
                model = settings.DEFAULT_MODEL,
                messages = messages,
                temperature = settings.DEFAULT_TEMPERATURE,
            )
        
        case _:
            raise ValueError(f"Unsupported provider: {settings.PROVIDER}") 


def extract_response_content(response: Any) -> str:
    if hasattr(response, "choices"):
        # OpenAI/Ollama
        return response.choices[0].message.content
    elif hasattr(response, "content"):
        # Claude
        return response.content[0].text
    elif isinstance(response, dict):
        # Dict compatibility (legacy OpenAI)
        return response["choices"][0]["message"]["content"]

    raise ValueError("Unsupported response format")