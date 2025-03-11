# dochub/tasks.py

from celery import shared_task
from .models import Document
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_document(document_id):
    """Process a document after upload"""
    try:
        document = Document.objects.get(id=document_id)
        
        # Update status to processing
        document.status = 'processing'
        document.save()
        
        # Placeholder for actual processing steps:
        # 1. Extract text from document
        # 2. Split text into chunks
        # 3. Generate embeddings
        # 4. Index in vector database
        # 5. Extract entities and build knowledge graph
        
        # For now, just mark as ready
        document.status = 'ready'
        document.save()
        
        return f"Document {document_id} processed successfully"
    
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return f"Document {document_id} not found"
    
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
        # Update document status to error
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'error'
            document.error_message = str(e)
            document.save()
        except:
            pass
        
        return f"Error processing document {document_id}: {str(e)}"