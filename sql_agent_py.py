"""PydanticAI agent for SQL query generation and execution."""

import logging
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel

from config_py import config
from database_py import db_manager

logger = logging.getLogger(__name__)


class SQLResponse(BaseModel):
    """Structured response from SQL agent."""
    sql_query: Optional[str] = Field(default=None, description="PostgreSQL query. Set to None/Null if chat.")
    explanation: str = Field(description="Brief explanation of the query OR the answer to the user")
    confidence: str = Field(description="Confidence level: high, medium, or low")


class ConversationDependency(BaseModel):
    """Dependency for conversation context."""
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0


class SQLAgent:
    """Agent for generating and executing SQL queries."""
    
    def __init__(self):
        """Initialize the SQL agent."""
        # 1. Load Schema (Data Structure)
        self.schema_info = self._load_yaml_schema()
        
        # 2. Load System Prompt (Personality & Instructions)
        self.system_prompt = self._build_system_prompt()
        
        self.model = GoogleModel(model_name=config.GEMINI_MODEL)
        self.agent = Agent(
            model=self.model,
            output_type=SQLResponse,
            system_prompt=self.system_prompt,
            retries=2
        )
        logger.info("SQL Agent initialized successfully")
    
    def _load_yaml_schema(self) -> Dict[str, Any]:
        """Load table schema from YAML file."""
        try:
            schema_path = Path(config.TABLE_SCHEMA_PATH)
            if not schema_path.exists():
                logger.warning(f"Schema file not found: {schema_path}")
                return {}
            
            with open(schema_path, 'r') as f:
                schema = yaml.safe_load(f)
            logger.info("Schema loaded successfully")
            return schema
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return {}

    def _build_system_prompt(self) -> str:
        """
        Reads system_prompt.txt and injects schema details.
        """
        # 1. Read the raw template file
        try:
            prompt_path = Path("system_prompt.txt") # Or use config path
            with open(prompt_path, "r") as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Could not load system_prompt.txt: {e}")
            # Fallback prompt if file is missing
            return "You are an AI assistant. Please convert natural language to SQL."

        # 2. Format the Schema Data into Strings
        # Default values in case schema loading failed
        table_name = self.schema_info.get('table_name', 'unknown_table')
        db_desc = self.schema_info.get('description', 'No description provided')
        
        # Format columns list
        columns_str = ""
        for col in self.schema_info.get('columns', []):
            columns_str += f"- **{col['name']}** ({col['type']}): {col.get('description', '')}\n"
        
        # Format notes list
        notes_str = ""
        if 'llm_query_notes' in self.schema_info:
            for note in self.schema_info['llm_query_notes']:
                notes_str += f"- {note['note']}\n"

        # 3. Inject data into the template
        final_prompt = template.format(
            database_description=db_desc,
            table_schema=columns_str,
            query_notes=notes_str,
            table_name=table_name
        )

        return final_prompt

    async def generate_sql(
            self, 
            user_question: str,
            conversation_history: Optional[List[Dict[str, str]]] = None
        ) -> SQLResponse:
            """Generate SQL query from natural language question."""
            try:
                deps = ConversationDependency(
                    conversation_history=conversation_history or []
                )
                
                context = user_question
                if conversation_history:
                    recent_context = conversation_history[-3:] 
                    context = "Previous context:\n"
                    for entry in recent_context:
                        context += f"Q: {entry.get('question', '')}\n"
                        sql_val = entry.get('sql')
                        if sql_val:
                            context += f"SQL: {sql_val}\n"
                    context += f"\nCurrent question: {user_question}"
                
                result = await self.agent.run(context, deps=deps)
                return result.output
                
            except Exception as e:
                logger.error(f"Error generating SQL: {e}")
                return SQLResponse(
                    sql_query=None,
                    explanation=f"Error: {str(e)}",
                    confidence="low"
                )
    
    def execute_query_with_retry(self, sql_query: str, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """Execute SQL query with automatic retry logic."""
        if max_retries is None:
            max_retries = config.MAX_QUERY_RETRIES
        
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            attempt += 1
            success, results, error = db_manager.execute_query(sql_query)
            
            if success:
                return {"success": True, "results": results, "rows": len(results) if results else 0, "error": None}
            
            last_error = error
            logger.warning(f"Query failed (attempt {attempt}): {error}")
        
        return {"success": False, "results": None, "error": last_error}
    
    async def process_question(self, user_question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Process user question end-to-end."""
        try:
            sql_response = await self.generate_sql(user_question, conversation_history)
            
            # If chat only (no SQL)
            if not sql_response.sql_query or sql_response.sql_query.strip().lower() == 'none':
                return {
                    "success": True,
                    "sql_query": None,
                    "explanation": sql_response.explanation,
                    "confidence": sql_response.confidence,
                    "results": None
                }
            
            # Execute SQL
            execution_result = self.execute_query_with_retry(sql_response.sql_query)
            
            return {
                "success": execution_result["success"],
                "sql_query": sql_response.sql_query,
                "explanation": sql_response.explanation,
                "confidence": sql_response.confidence,
                "results": execution_result["results"],
                "error": execution_result["error"]
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {"success": False, "error": str(e)}

# Global agent instance
sql_agent = SQLAgent()