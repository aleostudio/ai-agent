import requests
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
from app.core.logger import logger
from app.model.simple_agent_state import SimpleAgentState
import app.prompts as prompts

class SimpleAgent:

    # Agent instance with LangGraph workflow
    def __init__(self, model: ChatOllama):
        self.model = model
        self.workflow = StateGraph(SimpleAgentState)

        # LangGraph state creation
        self.workflow.add_node("SimpleAgentState", self.interact_with_model)
        
        # Execution flow definition (handoff) if we have other agents to call
        # self.workflow.add_node("SomeOtherAgent", self.some_other_agent)
        # self.workflow.add_edge("SimpleAgentState", "SomeOtherAgent")

        # Start point and graph compilation
        self.workflow.set_entry_point("SimpleAgentState")
        self.graph = self.workflow.compile()


    # Method to start the LangGraph graph
    def interact(self, prompt: str):
        state = {"prompt": prompt}
        output = self.graph.invoke(state)

        return {"agent_response": output}


    # Agent's entrypoint function
    def interact_with_model(self, state: SimpleAgentState) -> SimpleAgentState:        
        response = self.model.invoke(state["prompt"])
        state["ai_message"] = response
        state["generated_text"] = response.content

        return state


    # Example to call another agent via API
    def call_another_agent_api(self, state: SimpleAgentState) -> SimpleAgentState:

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