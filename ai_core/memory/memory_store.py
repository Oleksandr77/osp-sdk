import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MemoryScope(Enum):
    SESSION = "session"
    USER = "user"
    GLOBAL = "global"

class MemoryEvent:
    def __init__(self, event_type: str, key: str, old_value: Any, new_value: Any, actor_skill_id: str):
        self.event_type = event_type
        self.key = key
        self.old_value_hash = self._hash(old_value)
        self.new_value_hash = self._hash(new_value)
        self.timestamp = time.time()
        self.actor_skill_id = actor_skill_id

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(str(value).encode()).hexdigest()

class MemoryStore:
    def __init__(self, persistence_path: str = "data/memory.json"):
        self.persistence_path = persistence_path
        self._store: Dict[MemoryScope, Dict[str, Any]] = {
            MemoryScope.SESSION: {},
            MemoryScope.USER: {},
            MemoryScope.GLOBAL: {}
        }
        self._listeners = []
        self._load()

    def _load(self):
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, 'r') as f:
                    data = json.load(f)
                    # reconstitute enums
                    for scope_name, content in data.items():
                        # scope_name is "session", "user", "global"
                        # map back to Enum
                        for scope in MemoryScope:
                            if scope.value == scope_name:
                                self._store[scope] = content
                logger.info(f"Loaded memory from {self.persistence_path}")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")

    def _save(self):
        try:
            data = {}
            for scope, content in self._store.items():
                data[scope.value] = content
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            
            with open(self.persistence_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def get(self, key: str, scope: MemoryScope = MemoryScope.SESSION) -> Any:
        return self._store[scope].get(key)

    def set(self, key: str, value: Any, scope: MemoryScope = MemoryScope.SESSION, actor_skill_id: str = "system"):
        old_value = self._store[scope].get(key)
        self._store[scope][key] = value
        
        self._save() # Auto-save
        
        event = MemoryEvent("MEMORY_CHANGED", key, old_value, value, actor_skill_id)
        self._notify_listeners(event)
        logger.debug(f"Memory Set [{scope.value}]: {key} = {str(value)[:50]}...")

    def delete(self, key: str, scope: MemoryScope = MemoryScope.SESSION, actor_skill_id: str = "system"):
        if key in self._store[scope]:
            old_value = self._store[scope][key]
            del self._store[scope][key]
            self._save()
            event = MemoryEvent("MEMORY_DELETED", key, old_value, None, actor_skill_id)
            self._notify_listeners(event)

    def list(self, scope: MemoryScope = MemoryScope.SESSION) -> Dict[str, Any]:
        return self._store[scope].copy()

    def add_listener(self, callback):
        self._listeners.append(callback)

    def _notify_listeners(self, event: MemoryEvent):
        for callback in self._listeners:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in memory listener: {e}")
