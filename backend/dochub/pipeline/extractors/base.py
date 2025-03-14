# base.py (Text Extractor Interface)
from abc import ABC, abstractmethod

class TextExtractor(ABC):
    """Base interface for text extractors"""
    
    @abstractmethod
    def extract(self, file_path):
        """
        Extract text from a document file
        
        Args:
            file_path: Path to the document file
            
        Returns:
            str: Extracted text content
        """
        pass