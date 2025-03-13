# backend/dochub/services/document_service.py

import os
import logging
from django.conf import settings
from ..models import Document
from ..pipeline.extractors.docling_extractor import DoclingExtractor
from ..pipeline.splitters.langchain_splitter import LangchainSplitter
from ..pipeline.embeddings.openai_embeddings import OpenAIEmbeddingGenerator
from ..pipeline.indexers.chroma_indexer import ChromaIndexer
from ..pipeline.graphs.generator import GraphGenerator

logger = logging.getLogger(__name__)

class DocumentService:
    """
    Service for document processing operations.
    
    This service orchestrates the document processing pipeline:
    1. Extract text from document
    2. Split text into chunks
    3. Generate embeddings for chunks
    4. Index chunks and embeddings
    5. Generate knowledge graph
    """

    def __init__(self):
        """Initialize with pipeline components"""
        self.extractor = DoclingExtractor()
        self.splitter = LangchainSplitter()
        self.embedding_generator = OpenAIEmbeddingGenerator()
        self.indexer = ChromaIndexer()
        self.graph_generator = GraphGenerator()
    
    def process_document(self, document):
        """
        Process a document through the entire pipeline
        
        Args:
            document: Document instance to process
            
        Returns:
            dict: Processing results
        """
        try:
            # Get document file path
            file_path = document.file.path
            document_id = str(document.id)
            logger.info(f"Processing document '{document.name}' (ID: {document_id})")
            
            # STEP 1: Extract text from document
            logger.info(f"Extracting text from document: {file_path}")
            text = self.extractor.extract(file_path)
            
            if not text:
                error_msg = "No text extracted from document"
                logger.warning(f"{error_msg}: {document.name}")
                raise ValueError(error_msg)
            
            # STEP 2: Split text into chunks
            logger.info(f"Splitting text into chunks (length: {len(text)} characters)")
            chunks = self.splitter.split(text)
            
            if not chunks:
                error_msg = "Failed to split text into chunks"
                logger.warning(f"{error_msg}: {document.name}")
                raise ValueError(error_msg)
            
            logger.info(f"Created {len(chunks)} chunks")
            
            # STEP 3: Generate embeddings for chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            try:
                embeddings = self.embedding_generator.generate(chunks)
                
                if not embeddings or len(embeddings) != len(chunks):
                    error_msg = "Failed to generate embeddings for all chunks"
                    logger.warning(f"{error_msg}: Got {len(embeddings)} embeddings for {len(chunks)} chunks")
                    raise ValueError(error_msg)
            except Exception as e:
                # Instead of failing the entire pipeline, add a warning and continue with the rest of the steps
                # This allows other parts like graphs to still work
                logger.warning(f"Error generating embeddings (will continue without them): {str(e)}")
                embeddings = []  # Set empty embeddings
            
            # STEP 4: Index chunks and embeddings
            # Prepare metadata for indexing
            metadata = {
                "document_id": document_id,
                "name": document.name,
                "file_path": file_path,
                "file_type": document.file_type,
                "folder_id": str(document.folder.id) if document.folder else None,
                "folder_path": document.folder_path if document.folder else "Documents"
            }
            
            logger.info(f"Indexing {len(chunks)} chunks in vector database")
            self.indexer.index(chunks, embeddings, metadata)
            
            # STEP 5: Generate knowledge graph
            logger.info(f"Generating knowledge graph for document")
            
            # Default user ID (can be made configurable in the future)
            user_id = "system"  # or get from document owner if you implement authentication
            
            # Extract folder information for graph generation
            folder_id = str(document.folder.id) if document.folder else None
            
            # Process the document with graph generation
            graph_result = self.graph_generator.process_document(
                document_id,
                document.name,
                user_id,
                text,
                file_path=file_path,
                folder_path=document.folder_path if document.folder else "Documents",
                folder_id=folder_id,
                metadata=metadata,
                chunks=chunks
            )
            
            logger.info(f"Document {document_id} processed successfully")
            
            return {
                "document_id": document_id,
                "chunks_count": len(chunks),
                "entities_count": graph_result.get("entities_count", 0),
                "relationships_count": graph_result.get("relationships_count", 0),
                "related_documents": graph_result.get("related_documents", 0)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {str(e)}")
            raise
