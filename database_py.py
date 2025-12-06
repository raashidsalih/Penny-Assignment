"""Database connection and query execution utilities for MongoDB."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import json

from config_py import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections and query execution."""
    
    def __init__(self):
        """Initialize MongoDB client."""
        self.client: Optional[MongoClient] = None
        self.db = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the MongoDB client."""
        try:
            self.client = MongoClient(
                config.mongodb_uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=2
            )
            self.db = self.client[config.database_name]
            # Test connection
            self.client.admin.command('ping')
            logger.info("MongoDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise
    
    def get_collection(self, collection_name: str = None):
        """Get a MongoDB collection."""
        if self.db is None:
            raise RuntimeError("Database not initialized")
        
        if collection_name is None:
            collection_name = config.TABLE_NAME
        
        return self.db[collection_name]
    
    def execute_aggregation(
        self, 
        pipeline: List[Dict[str, Any]], 
        collection_name: str = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Execute a MongoDB aggregation pipeline and return results."""
        try:
            collection = self.get_collection(collection_name)
            results = list(collection.aggregate(pipeline))
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return True, results, None
                        
        except OperationFailure as e:
            return False, None, f"MongoDB Operation Error: {str(e)}"
        except Exception as e:
            return False, None, f"Database Error: {str(e)}"
    
    def execute_find(
        self, 
        query: Dict[str, Any] = None,
        projection: Dict[str, Any] = None,
        collection_name: str = None,
        limit: int = None,
        sort: List[Tuple[str, int]] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Execute a MongoDB find query and return results."""
        try:
            collection = self.get_collection(collection_name)
            cursor = collection.find(query or {}, projection or {})
            
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return True, results, None
                        
        except OperationFailure as e:
            return False, None, f"MongoDB Operation Error: {str(e)}"
        except Exception as e:
            return False, None, f"Database Error: {str(e)}"
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Execute a MongoDB query from a JSON string representation.
        This method accepts a JSON string containing the aggregation pipeline.
        """
        try:
            # Parse the query as JSON - it should be an aggregation pipeline
            pipeline = json.loads(query)
            
            if not isinstance(pipeline, list):
                # If it's a find-style query, wrap it
                pipeline = [{"$match": pipeline}]
            
            return self.execute_aggregation(pipeline)
                        
        except json.JSONDecodeError as e:
            return False, None, f"Query Parse Error: Invalid JSON - {str(e)}"
        except Exception as e:
            return False, None, f"Database Error: {str(e)}"
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close the MongoDB client."""
        if self.client:
            self.client.close()

# Global instance
db_manager = DatabaseManager()
