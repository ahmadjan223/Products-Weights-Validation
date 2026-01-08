"""
Data Retrieval Module
Handles MongoDB connection and data fetching by offer ID
"""
from pymongo import MongoClient
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataRetriever:
    """Handles MongoDB operations for product data retrieval"""
    
    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database
            collection_name: Name of the collection
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.client: Optional[MongoClient] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error connecting to MongoDB: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    def fetch_by_offer_id(self, offer_id: str) -> Optional[Dict[Any, Any]]:
        """
        Fetch product data from MongoDB using offer ID
        
        Args:
            offer_id: The offer ID to search for
            
        Returns:
            Document dict if found, None otherwise
            
        Raises:
            ValueError: If offer_id is invalid
            Exception: For database errors
        """
        if not self.client:
            raise ConnectionError("MongoDB client not initialized")
        
        try:
            # Convert offer_id to int for MongoDB query
            offer_id_int = int(offer_id)
            
            logger.info(f"🔍 Searching for offer ID: {offer_id}")
            
            db = self.client[self.database_name]
            collection = db[self.collection_name]
            
            # Search for document
            document = collection.find_one({"offerId": offer_id_int})
            
            if document:
                logger.info(f"✅ Document found for offer ID: {offer_id}")
                return document
            else:
                logger.warning(f"❌ No document found with offer ID: {offer_id}")
                return None
                
        except ValueError as e:
            logger.error(f"❌ Invalid offer ID format: {offer_id}")
            raise ValueError(f"Invalid offer ID format: {offer_id}") from e
        except Exception as e:
            logger.error(f"❌ Error fetching data: {e}")
            raise Exception(f"Database error: {e}") from e
    
    def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")
