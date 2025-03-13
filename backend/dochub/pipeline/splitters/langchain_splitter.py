# dochub/pipeline/splitters/langchain_splitter.py

import logging
from .base import TextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class LangchainSplitter(TextSplitter):
    """Text splitter implementation using LangChain's RecursiveCharacterTextSplitter"""
    
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        """
        Initialize with default chunk size and overlap
        
        Args:
            chunk_size: Default chunk size
            chunk_overlap: Default chunk overlap
        """
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
    
    def split(self, text, chunk_size=None, chunk_overlap=None):
        """
        Split text into chunks using LangChain's RecursiveCharacterTextSplitter
        
        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk (overrides default)
            chunk_overlap: Overlap between chunks (overrides default)
            
        Returns:
            list: List of text chunks
        """
        if not text:
            logger.warning("Empty text provided to splitter")
            return []
        
        # Use provided parameters or fall back to defaults
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        
        try:
            # Create splitter with specified parameters
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            
            # Split text and return chunks
            chunks = splitter.split_text(text)
            logger.info(f"Split text into {len(chunks)} chunks (size: {chunk_size}, overlap: {chunk_overlap})")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            # Fall back to simple splitting if LangChain fails
            simple_chunks = []
            for i in range(0, len(text), chunk_size - chunk_overlap):
                end = min(i + chunk_size, len(text))
                simple_chunks.append(text[i:end])
            logger.info(f"Used fallback splitting, created {len(simple_chunks)} chunks")
            return simple_chunks