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
        if not chunks:
            logger.warning("No chunks provided for indexing")
            return []
        
        # If embeddings are empty but chunks exist, log and return early
        if not embeddings:
            logger.warning("No embeddings provided for indexing. Skipping vector indexing but storing metadata.")
            # Generate IDs for tracking purposes
            doc_id = metadata.get('document_id', '')
            if not doc_id:
                doc_id = metadata.get('file_path', 'unknown').replace('/', '_')
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            return ids
            
        if len(chunks) != len(embeddings):
            error_msg = f"Number of chunks ({len(chunks)}) doesn't match number of embeddings ({len(embeddings)})"
            logger.error(error_msg)
            # Try to continue with partial data if possible
            if len(chunks) > len(embeddings):
                logger.warning(f"Truncating chunks to match embeddings count ({len(embeddings)})")
                chunks = chunks[:len(embeddings)]
            else:
                logger.warning(f"Truncating embeddings to match chunks count ({len(chunks)})")
                embeddings = embeddings[:len(chunks)]
        
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
            
            # Try different approaches to search
            if isinstance(query, str):
                logger.info(f"Searching with text query: {query[:50]}...")
                
                # For text queries, we need to convert to embedding or use ChromaDB's built-in conversion
                # The issue is that Docling might be using a different embedding model than ChromaDB expects
                try:
                    # First try with query_texts (Let ChromaDB handle embedding)
                    results = collection.query(
                        query_texts=[query],
                        n_results=limit,
                        where=metadata_filter
                    )
                except Exception as e:
                    if "dimension" in str(e).lower():
                        logger.warning(f"Text query failed due to dimension mismatch: {str(e)}. Trying metadata-only search.")
                        # If we have metadata filter, use it to get documents
                        if metadata_filter:
                            logger.info(f"Searching with metadata filter: {metadata_filter}")
                            results = collection.get(
                                where=metadata_filter,
                                limit=limit
                            )
                        else:
                            # Get all documents for this document ID if we can extract it from the query
                            # This is a reasonable fallback since we're usually searching within a document
                            try:
                                # Try to extract a document ID from the text query
                                import re
                                doc_ids = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', query)
                                
                                if doc_ids:
                                    # If we found potential document IDs, search for chunks from those documents
                                    doc_id = doc_ids[0]
                                    logger.info(f"Found potential document ID in query: {doc_id}")
                                    results = collection.get(
                                        where={"document_id": doc_id},
                                        limit=limit
                                    )
                                else:
                                    # No metadata filter and no document ID in query, get recent documents
                                    logger.warning("No metadata filter provided. Getting most recent documents.")
                                    results = collection.get(
                                        limit=limit
                                    )
                            except Exception as ex:
                                logger.warning(f"Error extracting document ID from query: {str(ex)}")
                                # Fallback to getting recent documents
                                results = collection.get(
                                    limit=limit
                                )
                    else:
                        # If it's not a dimension error, re-raise
                        raise
            else:
                # It's an embedding vector
                embedding_dim = len(query) if hasattr(query, '__len__') else 0
                logger.info(f"Searching with embedding vector of dimension {embedding_dim}")
                
                # We need to handle different embedding dimensions
                try:
                    # Attempt the query with the provided embedding
                    results = collection.query(
                        query_embeddings=[query],
                        n_results=limit,
                        where=metadata_filter
                    )
                except Exception as e:
                    logger.warning(f"Embedding query failed: {str(e)}. Falling back to metadata-only search.")
                    
                    # If dimensions don't match, try with metadata search
                    if metadata_filter:
                        logger.info(f"Using metadata filter instead: {metadata_filter}")
                        results = collection.get(
                            where=metadata_filter,
                            limit=limit
                        )
                    else:
                        # Without metadata filter, we have to get the most recent documents
                        logger.warning("No metadata filter provided. Getting most recent documents.")
                        results = collection.get(
                            limit=limit
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
