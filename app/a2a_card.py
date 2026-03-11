from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from app.core.config import settings


# Build agent card from settings
def build_agent_card() -> AgentCard:
    return AgentCard(
        name="AI agent",
        description="A general-purpose assistant that answers questions using an LLM.",
        url=settings.APP_URL,
        version=settings.APP_VERSION,
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="general-assistant",
                name="General Knowledge",
                description="Answers general questions, provides explanations, and helps with non-specialized tasks.",
                tags=["general", "assistant", "knowledge", "qa"],
                examples=["Tell me about Python", "What's the weather like?", "Explain quantum computing"],
            )
        ],
    )
