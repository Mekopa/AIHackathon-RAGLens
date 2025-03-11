# dochub/tasks.py

from celery import shared_task
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_document_task(document_id):
    """
    Process a document after upload.
    This task is called asynchronously when a document is uploaded.
    
    Args:
        document_id: ID of the document to process
    """
    try:
        # Import here to avoid circular import
        from .models import Document
        
        with transaction.atomic():
            # Get the document from the database
            document = Document.objects.select_for_update().get(id=document_id)
            
            # Update status to processing
            document.status = 'processing'
            document.save(update_fields=['status'])
        
        logger.info(f"Processing document {document_id}: {document.name}")
        
        # Placeholder for actual processing steps:
        # 1. Extract text from document
        # 2. Split text into chunks
        # 3. Generate embeddings
        # 4. Index in vector database
        # 5. Extract entities and build knowledge graph
        
        # For now, just mark as ready
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            document.status = 'ready'
            document.save(update_fields=['status'])
        
        logger.info(f"Document {document_id} processed successfully")
        return f"Document {document_id} processed successfully"
    
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return f"Document {document_id} not found"
    
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
        # Update document status to error
        try:
            from .models import Document
            with transaction.atomic():
                document = Document.objects.select_for_update().get(id=document_id)
                document.status = 'error'
                document.error_message = str(e)
                document.save(update_fields=['status', 'error_message'])
        except Exception as ex:
            logger.error(f"Failed to update document status: {str(ex)}")
        
        return f"Error processing document {document_id}: {str(e)}"