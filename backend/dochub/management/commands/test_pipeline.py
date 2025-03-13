# backend/dochub/management/commands/test_pipeline.py

import os
import time
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from dochub.models import Document
from dochub.services.document_service import DocumentService
from dochub.utils.pipeline_logger import PipelineLogger

class Command(BaseCommand):
    help = 'Test the document processing pipeline with a specific document'

    def add_arguments(self, parser):
        parser.add_argument('document_id', type=str, help='ID of the document to process')
        parser.add_argument('--save-artifacts', action='store_true', help='Save intermediate artifacts')
        parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
        parser.add_argument('--log-file', type=str, help='Path to log file')
        parser.add_argument('--openai-model', type=str, default='gpt-4o-mini', help='OpenAI model for graph generation')

    def setup_logging(self, verbose, log_file):
        """Setup logging configuration"""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO if verbose else logging.WARNING)
        
        # Configure pipeline test logger
        pipeline_logger = logging.getLogger('dochub.pipeline.test')
        pipeline_logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))
        pipeline_logger.addHandler(console_handler)
        
        # File handler if requested
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            pipeline_logger.addHandler(file_handler)
            self.stdout.write(f"Logging to {log_file}")

    def handle(self, *args, **options):
        document_id = options['document_id']
        save_artifacts = options['save_artifacts']
        verbose = options['verbose']
        log_file = options['log_file']
        openai_model = options['openai_model']
        
        # Setup logging
        self.setup_logging(verbose, log_file)
        
        try:
            # Get document
            try:
                document = Document.objects.get(id=document_id)
                self.stdout.write(f"Testing pipeline with document: {document.name} (ID: {document_id})")
            except Document.DoesNotExist:
                raise CommandError(f"Document with ID {document_id} does not exist")
            
            # Create pipeline logger
            logger = PipelineLogger(
                document_id=document_id,
                save_artifacts=save_artifacts
            )
            
            # Create a custom document service with the logger
            service = InstrumentedDocumentService(logger=logger, openai_model=openai_model)
            
            # Update document status to processing
            with transaction.atomic():
                document.status = 'processing'
                document.error_message = None
                document.save(update_fields=['status', 'error_message'])
            
            # Start testing
            self.stdout.write("Starting pipeline test...")
            
            start_time = time.time()
            logger.start_pipeline()
            
            # Process document
            try:
                result = service.process_document(document)
                
                # Update document status to ready
                with transaction.atomic():
                    document = Document.objects.get(id=document_id)
                    document.status = 'ready'
                    document.save(update_fields=['status'])
                
                logger.end_pipeline()
                
                # Output results
                elapsed_time = time.time() - start_time
                self.stdout.write(self.style.SUCCESS(
                    f"Pipeline test completed successfully in {elapsed_time:.2f} seconds"
                ))
                self.stdout.write(f"Results: {result}")
                
                # Show artifact location if saved
                if save_artifacts:
                    artifact_dir = os.path.join(settings.MEDIA_ROOT, 'pipeline_tests', document_id)
                    self.stdout.write(f"Artifacts saved to: {artifact_dir}")
                
            except Exception as e:
                # Update document status to error
                with transaction.atomic():
                    document = Document.objects.get(id=document_id)
                    document.status = 'error'
                    document.error_message = str(e)
                    document.save(update_fields=['status', 'error_message'])
                
                logger.log(f"Pipeline test failed: {str(e)}", logging.ERROR)
                logger.end_pipeline()
                
                raise CommandError(f"Pipeline test failed: {str(e)}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            return

# Instrumented version of DocumentService for testing
class InstrumentedDocumentService(DocumentService):
    """Enhanced DocumentService with logging instrumentation for testing"""
    
    def __init__(self, logger=None, openai_model='gpt-4o-mini'):
        """Initialize with a logger"""
        super().__init__()
        self.logger = logger
        self.openai_model = openai_model
        
        # Replace graph generator's model if specified
        if hasattr(self.graph_generator, 'schema') and hasattr(self.graph_generator.schema, 'get'):
            extraction_config = self.graph_generator.schema.get('extraction_config', {})
            extraction_config['model'] = openai_model
    
    @property
    def has_logger(self):
        """Check if logger is available"""
        return self.logger is not None
    
    def process_document(self, document):
        """Process document with logging"""
        if not self.has_logger:
            return super().process_document(document)
        
        try:
            # Get document file path
            file_path = document.file.path
            document_id = str(document.id)
            self.logger.log(f"Processing document '{document.name}' (ID: {document_id})")
            
            # STEP 1: Extract text from document
            self.logger.log(f"Extracting text from document: {file_path}")
            text = self.logger.log_step("extract_text")(self.extractor.extract)(file_path)
            
            if not text:
                error_msg = "No text extracted from document"
                self.logger.log(f"{error_msg}: {document.name}", logging.WARNING)
                raise ValueError(error_msg)
            
            # Log extracted text
            self.logger.log_extracted_text(text)
            
            # STEP 2: Split text into chunks
            self.logger.log(f"Splitting text into chunks (length: {len(text)} characters)")
            chunks = self.logger.log_step("split_text")(self.splitter.split)(text)
            
            if not chunks:
                error_msg = "Failed to split text into chunks"
                self.logger.log(f"{error_msg}: {document.name}", logging.WARNING)
                raise ValueError(error_msg)
            
            # Log chunks
            self.logger.log_text_chunks(chunks)
            
            # STEP 3: Generate embeddings for chunks
            self.logger.log(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = self.logger.log_step("generate_embeddings")(self.embedding_generator.generate)(chunks)
            
            if not embeddings or len(embeddings) != len(chunks):
                error_msg = "Failed to generate embeddings for all chunks"
                self.logger.log(f"{error_msg}: Got {len(embeddings)} embeddings for {len(chunks)} chunks", logging.WARNING)
                raise ValueError(error_msg)
            
            # Log embeddings
            self.logger.log_embeddings(embeddings)
            
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
            
            self.logger.log(f"Indexing {len(chunks)} chunks in vector database")
            chunk_ids = self.logger.log_step("index_chunks")(self.indexer.index)(chunks, embeddings, metadata)
            
            # STEP 5: Generate knowledge graph
            self.logger.log(f"Generating knowledge graph for document using model: {self.openai_model}")
            
            # Override the extract_entities_and_relations_openai method to log OpenAI I/O
            original_extract = self.graph_generator.extract_entities_and_relations_openai
            
            def logged_extract(*args, **kwargs):
                # Log the prompt
                text_to_extract = args[0] if args else kwargs.get('text', '')
                self.logger.log_openai_request(text_to_extract[:1000] + "..." if len(text_to_extract) > 1000 else text_to_extract)
                
                # Call original method
                result = original_extract(*args, **kwargs)
                
                # Log the response
                entities = result.get('entities', [])
                relationships = result.get('relationships', [])
                self.logger.log_graph_data(entities, relationships)
                
                return result
                
            # Replace the method temporarily
            self.graph_generator.extract_entities_and_relations_openai = logged_extract
            
            # Default user ID (can be made configurable in the future)
            user_id = "system"  # or get from document owner if you implement authentication
            
            # Extract folder information for graph generation
            folder_id = str(document.folder.id) if document.folder else None
            
            # Process the document with graph generation
            graph_result = self.logger.log_step("generate_graph")(self.graph_generator.process_document)(
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
            
            # Restore original method
            self.graph_generator.extract_entities_and_relations_openai = original_extract
            
            self.logger.log(f"Document {document_id} processed successfully")
            
            return {
                "document_id": document_id,
                "chunks_count": len(chunks),
                "entities_count": graph_result.get("entities_count", 0),
                "relationships_count": graph_result.get("relationships_count", 0),
                "related_documents": graph_result.get("related_documents", 0)
            }
            
        except Exception as e:
            self.logger.log(f"Error processing document {document.id}: {str(e)}", logging.ERROR)
            raise