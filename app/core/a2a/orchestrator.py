import re
import uuid
import httpx
from langchain_core.tools import BaseTool
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (MessageSendParams, Message, TextPart, SendMessageRequest, SendMessageSuccessResponse, Task)
from app.config import settings
from app.core.logger import logger


# Convert agent name to a valid LangChain tool name (alphanumeric + underscores)
def _sanitize_tool_name(name: str) -> str:
    return re.sub(r"\W", "_", name.strip()).strip("_").lower()


# Extract text from a SendMessageSuccessResponse result (Task or Message)
def _extract_parts_text(parts) -> str | None:
    if not parts:
        return None

    texts = [part.text for part in parts if hasattr(part, "text")]
    return "\n".join(texts) if texts else None


# Extract human-readable text from different result structures
def _extract_text_from_result(result) -> str:
    if isinstance(result, Task):
        status_message = getattr(result.status, "message", None)
        text = _extract_parts_text(getattr(status_message, "parts", None))
        if text:
            return text

        for message in reversed(result.history or []):
            if message.role != "agent":
                continue

            text = _extract_parts_text(getattr(message, "parts", None))
            if text:
                return text

        return str(result)

    text = _extract_parts_text(getattr(result, "parts", None))
    return text or str(result)


# Fetch registered agents from the A2A registry, excluding self
async def fetch_agents_from_registry() -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{settings.REGISTRY_URL}/agents", timeout=settings.REGISTRY_TIMEOUT_S)
            resp.raise_for_status()
            agents = resp.json()

            # Filter out self
            self_url = settings.APP_URL.rstrip("/")
            remote = [a for a in agents if a.get("url", "").rstrip("/") != self_url]

            logger.info(f"A2A registry returned {len(agents)} agent(s), {len(remote)} remote")
            return remote

        except Exception as e:
            logger.warning(f"Could not fetch agents from registry: {e}")
            return []


# LangChain tool that routes a message to a remote A2A agent
class A2ARoutingTool(BaseTool):
    name: str
    description: str
    agent_url: str

    async def _arun(self, message: str) -> str:
        try:
            async with httpx.AsyncClient() as http_client:
                # Resolve agent card
                resolver = A2ACardResolver(httpx_client=http_client, base_url=self.agent_url)
                card = await resolver.get_agent_card()

                # Create client and send message
                client = A2AClient(httpx_client=http_client, agent_card=card)
                request = SendMessageRequest(id="orchestrator-req", params=MessageSendParams(message=Message(messageId=str(uuid.uuid4()), role="user", parts=[TextPart(text=message)])))
                response = await client.send_message(request)

                # Extract result text
                if isinstance(response.root, SendMessageSuccessResponse):
                    return _extract_text_from_result(response.root.result)
                else:
                    error = response.root.error
                    return f"Agent error: {error.message}"

        except Exception as e:
            logger.error(f"A2A routing to {self.agent_url} failed: {e}")
            return f"Failed to reach agent: {e}"

    def _run(self, message: str) -> str:
        raise NotImplementedError("Use async")


# Create one A2ARoutingTool per remote agent
def build_orchestrator_tools(agents: list[dict]) -> list[A2ARoutingTool]:
    tools = []
    for agent in agents:
        url = agent.get("url", "")
        card = agent.get("card", {})
        name = card.get("name", "unknown")
        description = card.get("description", "")

        # Enrich description with skills
        skills = card.get("skills", [])
        if skills:
            skill_lines = ", ".join(s.get("name", "") for s in skills)
            description = f"{description} Skills: {skill_lines}"

        tool_name = f"a2a__{_sanitize_tool_name(name)}"
        tools.append(A2ARoutingTool(name=tool_name, description=description, agent_url=url))
        logger.info(f"A2A routing tool created: {tool_name} -> {url}")

    return tools
