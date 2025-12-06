"""Chat session management with MongoDB backend."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from decimal import Decimal
from bson import ObjectId
from pymongo import MongoClient, DESCENDING

from config_py import config

logger = logging.getLogger(__name__)


class ChatManager:
    """Manages chat sessions and message history using MongoDB."""
    
    def __init__(self, mongodb_uri: str, db_name: str):
        """
        Initialize chat manager with MongoDB connection.
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.sessions = self.db['chat_sessions']
        self.messages = self.db['chat_messages']
        
        # Create indexes for performance
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes for chat collections if they don't exist."""
        try:
            # Index for session queries
            self.sessions.create_index([("updated_at", DESCENDING)])
            self.sessions.create_index([("is_deleted", 1)])
            
            # Index for message queries
            self.messages.create_index([("session_id", 1), ("created_at", 1)])
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")
    
    def create_session(self, session_name: Optional[str] = None) -> str:
        """Create a new chat session. Returns session_id as string."""
        if not session_name:
            session_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        session_doc = {
            "session_name": session_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        
        try:
            result = self.sessions.insert_one(session_doc)
            session_id = str(result.inserted_id)
            logger.info(f"Created session {session_id}: {session_name}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all non-deleted chat sessions."""
        try:
            cursor = self.sessions.find(
                {"is_deleted": False},
                {"session_name": 1, "created_at": 1, "updated_at": 1}
            ).sort("updated_at", DESCENDING)
            
            sessions = []
            for doc in cursor:
                sessions.append({
                    "session_id": str(doc["_id"]),
                    "session_name": doc["session_name"],
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                })
            return sessions
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session."""
        try:
            cursor = self.messages.find(
                {"session_id": session_id}
            ).sort("created_at", 1)
            
            messages = []
            for doc in cursor:
                messages.append({
                    "message_id": str(doc["_id"]),
                    "role": doc["role"],
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                    "created_at": doc["created_at"]
                })
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to a session. Returns message_id as string."""
        
        def json_serializer(obj):
            """Helper to convert objects that aren't JSON serializable."""
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        try:
            # Serialize metadata if needed
            if metadata:
                # Convert to JSON and back to ensure all values are serializable
                metadata = json.loads(json.dumps(metadata, default=json_serializer))
            
            message_doc = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.utcnow()
            }
            
            result = self.messages.insert_one(message_doc)
            message_id = str(result.inserted_id)
            
            # Update session timestamp
            self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            
            return message_id
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a chat session."""
        try:
            result = self.sessions.update_one(
                {"_id": ObjectId(session_id), "is_deleted": False},
                {"$set": {"session_name": new_name, "updated_at": datetime.utcnow()}}
            )
            if result.modified_count > 0:
                logger.info(f"Renamed session {session_id} to '{new_name}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to rename session: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Soft delete a chat session."""
        try:
            result = self.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
            )
            if result.modified_count > 0:
                logger.info(f"Deleted session {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def get_conversation_context(
        self, 
        session_id: str, 
        last_n: int = 5
    ) -> List[Dict[str, str]]:
        """Get recent conversation context for the agent."""
        messages = self.get_session_messages(session_id)
        
        # Group into question-answer pairs
        context = []
        for i in range(0, len(messages) - 1, 2):
            if messages[i]['role'] == 'user' and messages[i + 1]['role'] == 'assistant':
                user_msg = messages[i]
                assistant_msg = messages[i + 1]
                
                # Get metadata
                metadata = assistant_msg.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                context.append({
                    'question': user_msg['content'],
                    'sql': metadata.get('sql_query', ''),
                    'response': assistant_msg['content']
                })
        
        return context[-last_n:] if context else []

# Global chat manager instance
chat_manager = ChatManager(config.mongodb_uri, config.database_name)
