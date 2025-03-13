# backend/dochub/pipeline/indexers/chroma_indexer.py

import os
import logging
import chromadb
from django.conf import settings
from .base import VectorIndexer

logger = logging.getLogger(__name__)

class ChromaIndexer(VectorIndexer):
    """Vector indexer implementation using ChromaDB"""
    
    def __init__(self, collection_name="documents", persist_directory=None):
        """
        Initialize the ChromaDB indexer
        
        Args:
            collection_name: Name of the collection in ChromaDB
            persist_directory: Directory to store the ChromaDB database
        """
        self.collection_name = collection_name
        
        # Get persist directory from settings or use default
        self.persist_directory = persist_directory or getattr(
            settings, 
            'CHROMA_PERSIST_DIRECTORY', 
            os.path.join(settings.MEDIA_ROOT, 'chroma_db')
        )
        
        # Ensure the persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        logger.info(f"ChromaDB will persist to: {self.persist_directory}")
    
    def _get_client(self):
        """
        Get a ChromaDB client
        
        Returns:
            chromadb.PersistentClient: ChromaDB client
        """
        return chromadb.PersistentClient(path=self.persist_directory)
    
    def _get_collection(self):
        """
        Get or create a ChromaDB collection
        
        Returns:
            chromadb.Collection: ChromaDB collection
        """
        client = self._get_client()
        return client.get_or_create_collection(name=self.collection_name)
    
    def _clean_metadata(self, metadata):
        """
        Clean metadata for ChromaDB (removes None values and converts complex types to strings)
        
        Args:
            metadata: Dictionary of metadata
            
        Returns:
            dict: Cleaned metadata dict
        """
        cleaned_metadata = {}
        for key, value in metadata.items():
            if value is not None:  # Skip None values
                # Ensure values are proper types for ChromaDB (str, int, float, bool)
                if isinstance(value, (str, int, float, bool)):
                    cleaned_metadata[key] = value
                else:
                    # Convert other types to strings
                    cleaned_metadata[key] = str(value)
        return cleaned_metadata
    
    def index(self, chunks, embeddings, metadata):
        """
        Index text chunks and their embeddings with metadata in ChromaDB
        
        Args:
            chunks: List of text chunks to index
            embeddings: List of embeddings for each chunk
            metadata: Dictionary of metadata to store with chunks
            
        Returns:
            list: List of IDs for indexed chunks
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings provided for indexing")
            return []
        
        if len(chunks) != len(embeddings):
            error_msg = f"Number of chunks ({len(chunks)}) doesn't match number of embeddings ({len(embeddings)})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Clean metadata - remove None values and convert to appropriate types
            cleaned_metadata = self._clean_metadata(metadata)
            
            # Get document identifier (prioritize ID over path)
            doc_id = metadata.get('document_id', '')
            if not doc_id:
                doc_id = metadata.get('file_path', 'unknown').replace('/', '_')
            
            # Create batch data for all chunks
            ids = []
            chunk_metadatas = []
            
            # Prepare metadata for each chunk
            for i in range(len(chunks)):
                # Generate a unique ID for each chunk
                chunk_id = f"{doc_id}_chunk_{i}"
                ids.append(chunk_id)
                
                # Copy the cleaned metadata and add chunk-specific information
                chunk_metadata = cleaned_metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["chunk_count"] = len(chunks)
                chunk_metadatas.append(chunk_metadata)
            
            # Add all chunks to the collection in a single batch operation
            collection = self._get_collection()
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Indexed {len(chunks)} chunks with embeddings for document {doc_id}")
            return ids
            
        except Exception as e:
            logger.error(f"Error indexing chunks in ChromaDB: {str(e)}")
            return []
    
    def search(self, query, metadata_filter=None, limit=5):
        """
        Search for similar chunks in ChromaDB
        
        Args:
            query: Search query (text string or embedding)
            metadata_filter: Filter by metadata (dict)
            limit: Maximum number of results
            
        Returns:
            dict: Search results containing documents, metadatas, distances, and ids
        """
        try:
            collection = self._get_collection()
            
            # Convert query to embedding if needed
            if isinstance(query, str):
                # This requires the embedding model, which we don't have here
                # For simplicity, we'll use the query as-is and let ChromaDB handle it
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=metadata_filter
                )
            else:
                # Use provided embedding directly
                results = collection.query(
                    query_embeddings=[query],
                    n_results=limit,
                    where=metadata_filter
                )
            
            # Reshape results for easier consumption
            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0],
                "ids": results.get("ids", [[]])[0]
            }
            
        except Exception as e:
            logger.error(f"Error searching in ChromaDB: {str(e)}")
            return {
                "documents": [],
                "metadatas": [],
                "distances": [],
                "ids": []
            }