import threading
import uuid
from datetime import datetime, timedelta
from app.core.config import settings
from typing import Dict, List, Optional

class ShortTermMemoryManager:

    def __init__(self, max_messages: int = settings.MAX_MEMORY_MESSAGES, max_users: int = 100, max_age_hours: int = 24):
        self.max_messages = max_messages
        self.max_users = max_users
        self.max_age_hours = max_age_hours
        self._lock = threading.RLock()
        self._memories: Dict[str, Dict] = {}


    def get_or_create(self, user_id: Optional[str] = None) -> str:
        with self._lock:
            if not user_id:
                user_id = str(uuid.uuid4())
            if user_id not in self._memories:
                self._memories[user_id] = {
                    "messages": [],
                    "created_at": datetime.now(),
                    "last_access": datetime.now()
                }
            else:
                self._memories[user_id]["last_access"] = datetime.now()
            return user_id


    def get_messages(self, user_id: str) -> List[Dict[str, str]]:
        with self._lock:
            return self._memories.get(user_id, {}).get("messages", []).copy()


    def update_messages(self, user_id: str, messages: List[Dict[str, str]]) -> None:
        with self._lock:
            if user_id in self._memories:
                trimmed = messages[-self.max_messages:]
                self._memories[user_id]["messages"] = trimmed
                self._memories[user_id]["last_access"] = datetime.now()


    def clear_user(self, user_id: str) -> bool:
        with self._lock:
            return self._memories.pop(user_id, None) is not None


    def get_all_users(self) -> List[Dict]:
        with self._lock:
            users = []
            for user_id, data in self._memories.items():
                users.append({
                    "user_id": user_id,
                    "message_count": len(data["messages"]),
                    "last_access": data["last_access"].isoformat(),
                    "created_at": data["created_at"].isoformat()
                })

            return sorted(users, key = lambda x: x["last_access"], reverse = True)


    def cleanup(self) -> int:
        with self._lock:
            cutoff = datetime.now() - timedelta(hours = self.max_age_hours)
            to_remove = [uid for uid, data in self._memories.items() if data["last_access"] < cutoff]

            for uid in to_remove:
                del self._memories[uid]

            if len(self._memories) > self.max_users:
                excess = sorted(self._memories.items(), key = lambda x: x[1]["last_access"])
                for uid, _ in excess[:len(self._memories) - self.max_users]:
                    del self._memories[uid]
                    to_remove.append(uid)

            return len(to_remove)
