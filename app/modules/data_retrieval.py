"""
Data Retrieval Module
Handles MongoDB connection and data fetching by offer ID
"""
from pymongo import MongoClient
from typing import Optional, Dict, Any, Union, List
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
    
    def fetch_by_offer_id(self, offer_id) -> Union[Optional[Dict[Any, Any]], Dict[str, Optional[Dict[Any, Any]]]]:
        """
        Fetch product data from MongoDB using offer ID(s)
        
        Args:
            offer_id: Single offer ID (str) or list of offer IDs (List[str])
            
        Returns:
            Single mode: Document dict if found, None otherwise
            Bulk mode: Dict mapping offer_id to document (or None if not found)
            
        Raises:
            ValueError: If offer_id is invalid
            Exception: For database errors
        """
        if not self.client:
            raise ConnectionError("MongoDB client not initialized")
        
        # Handle bulk mode (list of offer IDs)
        if isinstance(offer_id, list):
            return self._fetch_bulk(offer_id)
        
        # Handle single mode (string offer ID)
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
    
    def _fetch_bulk(self, offer_ids: List[str]) -> Dict[str, Optional[Dict[Any, Any]]]:
        """
        Internal method for bulk fetching
        """
        try:
            # Convert all offer_ids to int for MongoDB query
            offer_ids_int = []
            for oid in offer_ids:
                try:
                    offer_ids_int.append(int(oid))
                except ValueError as e:
                    logger.error(f"❌ Invalid offer ID format: {oid}")
                    raise ValueError(f"Invalid offer ID format: {oid}") from e
            
            logger.info(f"🔍 Bulk searching for {len(offer_ids)} offer IDs")
            
            db = self.client[self.database_name]
            collection = db[self.collection_name]
            
            # Bulk search using $in operator
            documents = list(collection.find({"offerId": {"$in": offer_ids_int}}))
            
            # Create mapping from offer_id to document
            result = {}
            found_offer_ids = set()
            
            for doc in documents:
                oid = str(doc["offerId"])
                result[oid] = doc
                found_offer_ids.add(oid)
            
            # Add None for missing offer_ids
            for oid in offer_ids:
                if oid not in found_offer_ids:
                    result[oid] = None
                    logger.warning(f"❌ No document found with offer ID: {oid}")
            
            logger.info(f"✅ Bulk fetch complete: {len(found_offer_ids)}/{len(offer_ids)} documents found")
            return result
                
        except Exception as e:
            logger.error(f"❌ Error in bulk fetch: {e}")
            raise Exception(f"Database error: {e}") from e
    
    def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
