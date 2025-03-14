# base.py (Vector Indexer Interface)
from abc import ABC, abstractmethod

class VectorIndexer(ABC):
    """Base interface for vector indexers"""
    
    @abstractmethod
    def index(self, chunks, embeddings, metadata):
        """
        Index chunks and embeddings
        
        Args:
            chunks: List of text chunks
            embeddings: List of embeddings
            metadata: Document metadata
            
        Returns:
            list: List of IDs for indexed chunks
        """
        pass
    
    @abstractmethod
    def search(self, query, metadata_filter=None, limit=5):
        """
        Search for similar chunks
        
        Args:
            query: Search query
            metadata_filter: Filter by metadata
            limit: Maximum number of results
            
        Returns:
            dict: Search results
        """
        pass