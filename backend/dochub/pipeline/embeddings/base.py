# base.py (Embedding Generator Interface)
from abc import ABC, abstractmethod

class EmbeddingGenerator(ABC):
    """Base interface for embedding generators"""
    
    @abstractmethod
    def generate(self, chunks):
        """
        Generate embeddings for text chunks
        
        Args:
            chunks: List of text chunks
            
        Returns:
            list: List of embeddings
        """
        pass