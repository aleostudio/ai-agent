import requests
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
from app.core.logger import logger
from app.model.simple_agent_state import SimpleAgentState
from app.memory.short_term_memory_manager import ShortTermMemoryManager
from app.memory.long_term_memory_manager import LongTermMemoryManager
import app.prompts as prompts

class SimpleAgent:

    # Agent instance with LangGraph workflow
    def __init__(self, model: ChatOllama, short_memory: ShortTermMemoryManager, long_memory: LongTermMemoryManager):
        self.model = model
        self.short_memory = short_memory
        self.long_memory = long_memory

        # LangGraph state creation
        self.workflow = StateGraph(SimpleAgentState)
        self.workflow.add_node("SimpleAgentState", self.interact_with_model)
        
        # Execution flow definition (handoff) if we have other agents to call
        # self.workflow.add_node("SomeOtherAgent", self.call_another_agent_api)
        # self.workflow.add_edge("SimpleAgentState", "SomeOtherAgent")

        # Start point and graph compilation
        self.workflow.set_entry_point("SimpleAgentState")
        self.graph = self.workflow.compile()


    # Method to start the LangGraph graph
    def interact(self, prompt: str, user_id: str = None):
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Generate new user id if empty and retrieve memories
        user_id = self.short_memory.get_or_create(user_id)
        short_memory = self.short_memory.get_messages(user_id)
        long_memory = self.long_memory.get_facts(user_id)

        # Convert long term facts into structured system messages
        context_messages = self.long_memory.format_facts_as_system_messages(long_memory)

        state = {
            "prompt": prompt.strip(),
            "user_id": user_id,
            "memory": context_messages + short_memory,
            "ai_message": None,
            "generated_text": ""
        }

        try:
            # Run graph workflow
            output = self.graph.invoke(state)

            # Thread-safe memory update
            self.short_memory.update_messages(user_id, output["memory"])

            return {
                "agent_response": output, 
                "user_id": user_id, 
                "memory_size": len(output["memory"])
            }

        except Exception as e:
            logger.error(f"Error in interact workflow for user {user_id}: {e}")
            raise


    # Agent's entrypoint function
    def interact_with_model(self, state: SimpleAgentState) -> SimpleAgentState:
        prompt = state["prompt"]
        user_id = state["user_id"]
        memory = state["memory"]
        
        # Get messages from memory and append current user prompt
        messages = [m for m in memory if "role" in m and "content" in m]
        messages.append({"role": "user", "content": prompt})

        try:
            # Invoke model with all messages or prompt only if it is the first message
            response = self.model.invoke(messages if len(messages) > 1 else prompt)
            updated_memory = messages + [{"role": "assistant", "content": response.content}]

            # Extract facts from prompt and save them in long-term memory
            self.extract_and_store_facts(user_id, prompt)
            
            state["memory"] = updated_memory[-self.short_memory.max_messages:]
            state["ai_message"] = response
            state["generated_text"] = response.content

        except Exception as e:
            logger.error(f"Model error for user {user_id}: {e}")
            state["generated_text"] = f"Error: {str(e)}"
            state["ai_message"] = None

        return state


    def extract_and_store_facts(self, user_id: str, prompt: str):
        prompt_lower = prompt.lower()

        if "mi chiamo" in prompt_lower:
            name = prompt_lower.split("mi chiamo")[-1].strip().split()[0]
            self.long_memory.add_fact(user_id, "names", name)

        if "mio figlio si chiama" in prompt_lower:
            name = prompt_lower.split("mio figlio si chiama")[-1].strip().split()[0]
            self.long_memory.add_fact(user_id, "children", name)


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
