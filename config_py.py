"""Configuration management for the application."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "penny_db")
    
    # Collection/Table name for procurement data
    TABLE_NAME: str = os.getenv("TABLE_NAME", "california_procurement")
    
    # File Paths
    TABLE_SCHEMA_PATH: str = os.getenv("TABLE_SCHEMA_PATH", "table_schema.yaml")
    PROMPT_PATH: str = os.getenv("PROMPT_PATH", "prompt.txt")
    
    # AI Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # Application Settings
    MAX_QUERY_RETRIES: int = int(os.getenv("MAX_QUERY_RETRIES", "3"))
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "30"))
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Example Queries
    EXAMPLE_QUERIES: List[str] = os.getenv(
        "EXAMPLE_QUERIES", 
        "What was the total procurement spending in fiscal year 2014-15?"
    ).split("|")
    
    @property
    def mongodb_uri(self) -> str:
        """Return MongoDB connection URI."""
        return self.MONGODB_URI
    
    @property
    def database_name(self) -> str:
        """Return MongoDB database name."""
        return self.MONGODB_DB_NAME
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required but not set")
        return True


# Global config instance
config = Config()
