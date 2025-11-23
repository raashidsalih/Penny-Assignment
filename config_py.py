"""Configuration management for the application."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # Database Configuration
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "penny_db")
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
    def database_url(self) -> str:
        """Construct database connection URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required but not set")
        return True


# Global config instance
config = Config()
