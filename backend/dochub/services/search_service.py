# backend/dochub/tasks/document_tasks.py

import os
import logging
from celery import shared_task
from django.db import transaction
from ..models import Document
from ..services.document_service import DocumentService

logger = logging.getLogger(__name__)

@shared_task
def process_document_task(document_id):
    """
    Celery task to process a document
    
    Args:
        document_id: ID of the document to process
        
    Returns:
        dict: Processing results
    """
    logger.info(f"Starting document processing task for document {document_id}")
    
    try:
        # Get document from database with lock
        with transaction.atomic():
            try:
                document = Document.objects.select_for_update().get(id=document_id)
                
                # Set status to processing
                if document.status != 'processing':
                    document.status = 'processing'
                    document.error_message = None
                    document.save(update_fields=['status', 'error_message'])
                
            except Document.DoesNotExist:
                logger.error(f"Document {document_id} not found")
                return {"error": f"Document {document_id} not found"}
        
        # Process document using the document service
        service = DocumentService()
        result = service.process_document(document)
        
        # Update document status to ready
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            document.status = 'ready'
            document.save(update_fields=['status'])
        
        logger.info(f"Document {document_id} processed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
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