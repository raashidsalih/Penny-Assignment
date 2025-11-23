"""Chat session management with PostgreSQL backend."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

from config_py import config

logger = logging.getLogger(__name__)


class ChatManager:
    """Manages chat sessions and message history."""
    
    def __init__(self, connection_string: str):
        """
        Initialize chat manager with database connection.
        Note: Assumes tables defined in chat_schema.sql exist.
        """
        self.connection_string = connection_string
        # initialization logic removed as requested
    
    def create_session(self, session_name: Optional[str] = None) -> int:
        """Create a new chat session."""
        if not session_name:
            session_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        query = """
        INSERT INTO chat_sessions (session_name, created_at, updated_at)
        VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING session_id;
        """
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (session_name,))
                    result = cur.fetchone()
                    conn.commit()
                    session_id = result['session_id']
                    logger.info(f"Created session {session_id}: {session_name}")
                    return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all non-deleted chat sessions."""
        query = """
        SELECT session_id, session_name, created_at, updated_at
        FROM chat_sessions
        WHERE is_deleted = FALSE
        ORDER BY updated_at DESC;
        """
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    sessions = cur.fetchall()
                    return sessions
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def get_session_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a session."""
        query = """
        SELECT message_id, role, content, metadata, created_at
        FROM chat_messages
        WHERE session_id = %s
        ORDER BY created_at ASC;
        """
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (session_id,))
                    messages = cur.fetchall()
                    return messages
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a message to a session."""
        insert_query = """
        INSERT INTO chat_messages (session_id, role, content, metadata, created_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING message_id;
        """
        
        update_query = """
        UPDATE chat_sessions
        SET updated_at = CURRENT_TIMESTAMP
        WHERE session_id = %s;
        """

        def json_serializer(obj):
            """Helper to convert objects that aren't JSON serializable."""
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Type {type(obj)} not serializable")
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    metadata_json = json.dumps(metadata, default=json_serializer) if metadata else None
                    
                    cur.execute(insert_query, (session_id, role, content, metadata_json))
                    result = cur.fetchone()
                    message_id = result['message_id']
                    
                    # Update session timestamp
                    cur.execute(update_query, (session_id,))
                    
                    conn.commit()
                    return message_id
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
    
    def rename_session(self, session_id: int, new_name: str) -> bool:
        """Rename a chat session."""
        query = """
        UPDATE chat_sessions
        SET session_name = %s, updated_at = CURRENT_TIMESTAMP
        WHERE session_id = %s AND is_deleted = FALSE;
        """
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (new_name, session_id))
                    conn.commit()
                    logger.info(f"Renamed session {session_id} to '{new_name}'")
                    return True
        except Exception as e:
            logger.error(f"Failed to rename session: {e}")
            return False
    
    def delete_session(self, session_id: int) -> bool:
        """Soft delete a chat session."""
        query = """
        UPDATE chat_sessions
        SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
        WHERE session_id = %s;
        """
        
        try:
            with psycopg.connect(self.connection_string, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (session_id,))
                    conn.commit()
                    logger.info(f"Deleted session {session_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def get_conversation_context(
        self, 
        session_id: int, 
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
                
                # Parse metadata for SQL query
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
chat_manager = ChatManager(config.database_url)