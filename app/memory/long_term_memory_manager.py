import threading
from typing import Dict, List, Optional

class LongTermMemoryManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._memories: Dict[str, Dict[str, List[str]]] = {}


    def add_fact(self, user_id: str, category: str, fact: str):
        with self._lock:
            if user_id not in self._memories:
                self._memories[user_id] = {}
            if category not in self._memories[user_id]:
                self._memories[user_id][category] = []
            if fact not in self._memories[user_id][category]:
                self._memories[user_id][category].append(fact)


    def get_facts(self, user_id: str, category: Optional[str] = None) -> Dict[str, List[str]]:
        with self._lock:
            if user_id not in self._memories:
                return {}
            if category:
                return {category: self._memories[user_id].get(category, [])}
            return self._memories[user_id].copy()


    def clear_user(self, user_id: str) -> bool:
        with self._lock:
            return self._memories.pop(user_id, None) is not None


    def get_all_users(self) -> List[str]:
        with self._lock:
            return list(self._memories.keys())


    def format_facts_as_system_messages(self, facts: Dict[str, List[str]]) -> List[Dict[str, str]]:
        system_messages = []
        for category, entries in facts.items():
            if entries:
                content = f"User {category}: {', '.join(entries)}"
                system_messages.append({"role": "system", "content": content})

        return system_messages
