# Import tasks to ensure they're registered with Celery
from .document_tasks import (
    process_document_task,
    cleanup_processing_documents,
    reprocess_failed_document,
    mock_process_document_task
)

__all__ = [
    'process_document_task',
    'cleanup_processing_documents',
    'reprocess_failed_document',
    'mock_process_document_task'
]