import requests
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph
from app.core.logger import logger
from app.core.config import settings
from app.model.simple_agent_state import SimpleAgentState
import app.prompts as prompts

class SimpleAgent:

    # Agent instance with LangGraph workflow
    def __init__(self, model: ChatOllama, max_memory_messages: int = settings.MAX_MEMORY_MESSAGES):
        self.model = model
        self.max_memory_messages = max_memory_messages
        self.user_memories: Dict[str, List[Dict[str, str]]] = {}

        # Thread-safe storage per memoria utenti con timestamp
        self._memory_lock = threading.RLock()

        # LangGraph state creation
        self.workflow = StateGraph(SimpleAgentState)
        self.workflow.add_node("SimpleAgentState", self.interact_with_model)
        
        # Execution flow definition (handoff) if we have other agents to call
        # self.workflow.add_node("SomeOtherAgent", self.some_other_agent)
        # self.workflow.add_edge("SimpleAgentState", "SomeOtherAgent")

        # Start point and graph compilation
        self.workflow.set_entry_point("SimpleAgentState")
        self.graph = self.workflow.compile()


    # Method to start the LangGraph graph
    def interact(self, prompt: str, user_id: str = None):
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Generate new user id if empty
        if user_id is None:
            user_id = str(uuid.uuid4())
            logger.info(f"Generated new user: {user_id}")

        # Thread-safe memory access
        with self._memory_lock:

            if user_id not in self.user_memories:
                # Set user id and dates in memory if not exists
                self.user_memories[user_id] = {"messages": [], "last_access": datetime.now(), "created_at": datetime.now()}
                logger.info(f"New memory initialized for user: {user_id}")
            else:
                # Update last access only
                self.user_memories[user_id]["last_access"] = datetime.now()

            user_memory = self.user_memories[user_id]["messages"].copy()

        state = {
            "prompt": prompt.strip(),
            "user_id": user_id,
            "memory": user_memory,
            "ai_message": None,
            "generated_text": ""
        }

        try:
            # Run graph workflow
            output = self.graph.invoke(state)

            # Thread-safe memory update
            with self._memory_lock:
                if user_id in self.user_memories:  # Verifica che esista ancora
                    self.user_memories[user_id]["messages"] = output["memory"]
                    self.user_memories[user_id]["last_access"] = datetime.now()

            return {"agent_response": output, "user_id": user_id, "memory_size": len(output["memory"])}

        except Exception as e:
            logger.error(f"Error in interact workflow for user {user_id}: {e}")
            raise


    # Agent's entrypoint function
    def interact_with_model(self, state: SimpleAgentState) -> SimpleAgentState:
        prompt = state["prompt"]
        user_id = state["user_id"]
        memory = state["memory"]
        messages = []

        # Append messages from memory
        for msg in memory:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                logger.warning(f"Invalid message structure in memory for user {user_id}: {msg}")
                continue
            
            messages.append({"role": msg["role"], "content": str(msg["content"])})

        # Append user prompt
        messages.append({"role": "user", "content": prompt})

        # Cut oldest messages (sliding window)
        if len(messages) > self.max_memory_messages:
            messages = messages[-self.max_memory_messages:]
            logger.info(f"Sliding window applied for user {user_id}. Messages: {len(messages)}")

        try:
            if len(messages) == 1:
                # First message, send prompt only
                response = self.model.invoke(prompt)
            else:
                # Existing chat, send all messages
                response = self.model.invoke(messages)

            updated_memory = []

            # Update memory with old messages and new prompt and model response
            if len(messages) > 1:
                updated_memory.extend([
                    {"role": msg["role"], "content": msg["content"]} 
                    for msg in messages[:-1]
                ])

            updated_memory.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": response.content}])

            # Cut oldest messages again (sliding window)
            if len(updated_memory) > self.max_memory_messages:
                updated_memory = updated_memory[-self.max_memory_messages:]

            # Update state
            state["memory"] = updated_memory
            state["ai_message"] = response
            state["generated_text"] = response.content
            
        except Exception as e:
            logger.error(f"Error interacting with model for user {user_id}: {e}")
            state["generated_text"] = f"Error: {str(e)}"
            state["ai_message"] = None
        
        return state


    # Clear memory for given user
    def clear_user_memory(self, user_id: str) -> bool:
        with self._memory_lock:
            if user_id in self.user_memories:
                del self.user_memories[user_id]
                logger.info(f"Memory erased for user: {user_id}")
                return True

            return False


    # Get memory for given user
    def get_user_memory(self, user_id: str) -> Dict:
        with self._memory_lock:
            if user_id not in self.user_memories:
                return {"exists": False, "messages": 0}

            user_data = self.user_memories[user_id]
            memory = user_data["messages"]

            return {
                "exists": True,
                "messages": len(memory),
                "last_messages": memory[-6:] if len(memory) > 0 else [],
                "last_access": user_data["last_access"].isoformat(),
                "created_at": user_data["created_at"].isoformat()
            }


    # Active users with existing memory
    def get_active_users(self) -> List[str]:
        with self._memory_lock:
            users = []
            for user_id, data in self.user_memories.items():
                users.append({
                    "user_id": user_id,
                    "message_count": len(data["messages"]),
                    "last_access": data["last_access"].isoformat(),
                    "created_at": data["created_at"].isoformat()
                })
            
            # Sort by last access
            users.sort(key = lambda x: x["last_access"], reverse = True)

            return users


    # Erase all user memories
    def cleanup_old_memories(self, max_users: int = 100, max_age_hours: int = 24) -> int:
        removed_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._memory_lock:
            users_to_remove = []
            for user_id, data in self.user_memories.items():
                if data["last_access"] < cutoff_time:
                    users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                del self.user_memories[user_id]
                removed_count += 1
                logger.info(f"Removed inactive user memory: {user_id}")
            
            if len(self.user_memories) > max_users:
                sorted_users = sorted(
                    self.user_memories.items(),
                    key=lambda x: x[1]["last_access"]
                )
                
                excess_count = len(self.user_memories) - max_users
                for user_id, _ in sorted_users[:excess_count]:
                    del self.user_memories[user_id]
                    removed_count += 1
                    logger.info(f"Removed old user memory (capacity): {user_id}")
        
        if removed_count > 0:
            logger.info(f"Cleanup completed. Removed {removed_count} user memories")
        
        return removed_count


    # Memory stats
    def get_memory_stats(self) -> Dict:
        with self._memory_lock:
            if not self.user_memories:
                return {"total_users": 0, "total_messages": 0, "avg_messages_per_user": 0, "oldest_user": None, "most_active_user": None}
            
            total_messages = sum(len(data["messages"]) for data in self.user_memories.values())
            avg_messages = total_messages / len(self.user_memories)
            oldest_user = min(self.user_memories.items(), key=lambda x: x[1]["created_at"])
            most_active_user = max(self.user_memories.items(), key=lambda x: len(x[1]["messages"]))
            
            return {
                "total_users": len(self.user_memories),
                "total_messages": total_messages,
                "avg_messages_per_user": round(avg_messages, 2),
                "oldest_user": {
                    "user_id": oldest_user[0],
                    "created_at": oldest_user[1]["created_at"].isoformat(),
                    "message_count": len(oldest_user[1]["messages"])
                },
                "most_active_user": {
                    "user_id": most_active_user[0],
                    "message_count": len(most_active_user[1]["messages"]),
                    "last_access": most_active_user[1]["last_access"].isoformat()
                }
            }


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
