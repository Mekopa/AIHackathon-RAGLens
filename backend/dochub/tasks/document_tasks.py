# backend/dochub/tasks/document_tasks.py

import os
import logging
import time
from celery import shared_task
from django.db import transaction
from django.conf import settings

from ..models import Document
from ..services.document_service import DocumentService
from ..pipeline.extractors.docling_extractor import DoclingExtractor
from ..pipeline.splitters.langchain_splitter import LangchainSplitter
from ..pipeline.embeddings.openai_embeddings import OpenAIEmbeddingGenerator
from ..pipeline.indexers.chroma_indexer import ChromaIndexer
from ..pipeline.graphs.generator import GraphGenerator

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_task(self, document_id):
    """
    Celery task to process a document through the entire pipeline
    
    This task:
    1. Extracts text from the document
    2. Splits text into chunks
    3. Generates embeddings for each chunk
    4. Indexes chunks in the vector database
    5. Generates a knowledge graph
    6. Updates document status accordingly
    
    Args:
        document_id: ID of the document to process
        
    Returns:
        dict: Processing results
    """
    logger.info(f"Starting document processing task for document {document_id}")
    processing_start_time = time.time()
    
    try:
        # Get document from database with lock
        with transaction.atomic():
            try:
                document = Document.objects.select_for_update().get(id=document_id)
                
                # Set status to processing if not already
                if document.status != 'processing':
                    document.status = 'processing'
                    document.error_message = None
                    document.save(update_fields=['status', 'error_message'])
                
                logger.info(f"Processing document: {document.name} (ID: {document_id})")
                
            except Document.DoesNotExist:
                logger.error(f"Document {document_id} not found")
                return {"error": f"Document {document_id} not found"}
        
        # Process document using the document service
        service = DocumentService()
        
        try:
            # Full pipeline processing
            result = service.process_document(document)
            processing_time = time.time() - processing_start_time
            
            # Update document status to ready
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'ready'
                document.save(update_fields=['status'])
            
            logger.info(f"Document {document_id} processed successfully in {processing_time:.2f}s: {result}")
            return {
                "status": "success",
                "document_id": document_id,
                "processing_time": processing_time,
                "result": result
            }
            
        except Exception as processing_error:
            # Handle processing error
            logger.error(f"Error during document processing: {str(processing_error)}")
            
            # Update document status to error
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'error'
                document.error_message = str(processing_error)
                document.save(update_fields=['status', 'error_message'])
            
            # Check if we should retry
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying document processing for {document_id} ({self.request.retries + 1}/{self.max_retries})")
                raise self.retry(exc=processing_error)
            
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(processing_error)
            }
        
    except Exception as e:
        logger.error(f"Critical error in process_document_task: {str(e)}")
        
        # Update document status to error (if document exists)
        try:
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'error'
                document.error_message = f"Critical task error: {str(e)}"
                document.save(update_fields=['status', 'error_message'])
        except Exception as ex:
            logger.error(f"Failed to update document status: {str(ex)}")
        
        return {
            "status": "error",
            "document_id": document_id,
            "error": f"Critical task error: {str(e)}"
        }

@shared_task
def cleanup_processing_documents():
    """
    Cleanup task to fix any documents stuck in 'processing' state for too long
    
    This task will find documents that have been in 'processing' state for more than
    30 minutes and mark them as 'error' with an appropriate message.
    """
    import datetime
    from django.utils import timezone
    
    # Find documents that have been processing for more than 30 minutes
    time_threshold = timezone.now() - datetime.timedelta(minutes=30)
    
    stuck_documents = Document.objects.filter(
        status='processing',
        updated_at__lt=time_threshold
    )
    
    count = 0
    for doc in stuck_documents:
        doc.status = 'error'
        doc.error_message = "Processing timed out. The document was stuck in processing state for too long."
        doc.save(update_fields=['status', 'error_message'])
        count += 1
    
    if count > 0:
        logger.info(f"Cleanup task fixed {count} documents stuck in 'processing' state")
    
    return count

@shared_task
def reprocess_failed_document(document_id):
    """
    Task to retry processing a document that previously failed
    
    Args:
        document_id: ID of the document to reprocess
    """
    try:
        # Get document from database
        document = Document.objects.get(id=document_id)
        
        # Only reprocess if it's in error state
        if document.status == 'error':
            # Reset status to processing
            document.status = 'processing'
            document.error_message = None
            document.save(update_fields=['status', 'error_message'])
            
            # Queue the processing task
            process_document_task.delay(str(document_id))
            
            return {"status": "reprocessing", "document_id": document_id}
        else:
            return {
                "status": "skipped", 
                "document_id": document_id,
                "reason": f"Document is not in error state (current: {document.status})"
            }
    
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for reprocessing")
        return {"status": "error", "error": f"Document {document_id} not found"}
    
    except Exception as e:
        logger.error(f"Error queuing document {document_id} for reprocessing: {str(e)}")
        return {"status": "error", "error": str(e)}

# For testing/development only - simplified version that just marks documents as ready
@shared_task
def mock_process_document_task(document_id):
    """
    A simpler version of the document processing task for development/testing
    This skips actual processing and just marks documents as ready after a delay
    
    Args:
        document_id: ID of the document to process
    """
    try:
        # Add a delay to simulate processing time
        import time
        time.sleep(5)  # 5 second delay
        
        # Update document status to ready
        with transaction.atomic():
            try:
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'ready'
                document.save(update_fields=['status'])
                
                logger.info(f"Mock processed document {document_id}")
                return {"status": "success", "document_id": document_id}
                
            except Document.DoesNotExist:
                logger.error(f"Document {document_id} not found")
                return {"error": f"Document {document_id} not found"}
                
    except Exception as e:
        logger.error(f"Error in mock processing: {str(e)}")
        
        # Update document status to error
        try:
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'error'
                document.error_message = str(e)
                document.save(update_fields=['status', 'error_message'])
                
        except Exception as ex:
            logger.error(f"Failed to update document status: {str(ex)}")
        
        return {"error": str(e)}