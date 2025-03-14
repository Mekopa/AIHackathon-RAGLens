# base.py (Text Splitter Interface)
from abc import ABC, abstractmethod

class TextSplitter(ABC):
    """Base interface for text splitters"""
    
    @abstractmethod
    def split(self, text, chunk_size=1000, chunk_overlap=200):
        """
        Split text into chunks
        
        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            list: List of text chunks
        """
        pass