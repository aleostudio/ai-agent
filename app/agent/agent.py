import requests
from typing import Any
from langgraph.graph import StateGraph
from app.core.provider import ChatModel
from app.core.logger import logger
from app.model.agent_state import AgentState
from app.core.provider import extract_response_content
from app.core.config import settings

class Agent:

    # Agent instance with LangGraph workflow
    def __init__(self, model: ChatModel):
        self.model = model
        self.workflow = StateGraph(AgentState)

        # LangGraph state creation
        self.workflow.add_node("AgentState", self.interact_with_model)
        
        # Execution flow definition (handoff) if we have other agents to call
        # self.workflow.add_node("SomeOtherAgent", self.some_other_agent)
        # self.workflow.add_edge("AgentState", "SomeOtherAgent")

        # Start point and graph compilation
        self.workflow.set_entry_point("AgentState")
        self.graph = self.workflow.compile()


    # Method to start the LangGraph graph
    def interact(self, prompt: str):
        state = {
            "prompt": prompt,
        }

        output = self.graph.invoke(state)

        return {
            "agent_response": output,
        }


    # Agent's entrypoint function
    def interact_with_model(self, state: AgentState) -> AgentState:
        messages = [
            {"role": "system", "content": settings.DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": state["prompt"]}
        ]
        response = self.model(messages)

        # Response adapter depending by chosen provider
        state["response"] = extract_response_content(response)
        
        return state


    # Example to call another agent via API
    def call_another_agent_api(self, state: AgentState) -> AgentState:

        try:
            logger.info("Calling remote agent")

            response = requests.post("http://agent_url/interact", json = {
                "input_var": "some_val"
            })
            response.raise_for_status()
            result = response.json()

            state["some_property"] = result.get("some_result", "default value")

        except requests.RequestException as e:
            logger.error(f"Error calling agent API: {e}")

            state["some_property"] = "API Error"
        
        return state
