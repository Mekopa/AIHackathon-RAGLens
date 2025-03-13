# backend/dochub/signals.py

import os
import shutil
import logging
import mimetypes
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from .models import Document, Folder
# Import tasks properly to ensure they're registered with Celery
from dochub.tasks.document_tasks import process_document_task

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Document)
def handle_document_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save events on Document model.
    
    1. Updates file metadata when a document is created
    2. Triggers the document processing task
    
    Args:
        sender: The model class
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
    """
    if created and instance.file:
        logger.debug(f"Document created: {instance.id} - {instance.name}")
        
        try:
            # Update file metadata using mimetypes
            file_path = instance.file.path
            
            # Determine file type from filename or content type
            file_mimetype, _ = mimetypes.guess_type(instance.file.name)
            if file_mimetype:
                instance.file_type = file_mimetype
            else:
                # Fallback to extension
                _, ext = os.path.splitext(instance.file.name)
                instance.file_type = ext.lstrip('.').lower() if ext else 'unknown'

            # Set file size
            instance.size = instance.file.size
            
            # Determine if document should be processed
            should_process = True
            
            # Skip processing for certain file types if needed
            unsupported_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if instance.file_type in unsupported_types:
                logger.info(f"Skipping processing for unsupported file type: {instance.file_type}")
                # Set status to ready immediately for unsupported file types
                instance.status = 'ready'
                should_process = False
            else:
                instance.status = 'processing'
            
            # Save changes (without triggering this signal again)
            Document.objects.filter(id=instance.id).update(
                file_type=instance.file_type,
                size=instance.size,
                status=instance.status
            )
            
            logger.debug(f"Updated metadata for document {instance.id}: type={instance.file_type}, size={instance.size}, status={instance.status}")
            
            # Queue document processing task if needed
            if should_process:
                logger.info(f"Queuing document processing task for {instance.id}")
                
                # DEVELOPMENT ENVIRONMENT CHECK 
                # If in development with DEBUG=True, use the mock processor for faster testing
                from django.conf import settings
                if getattr(settings, 'DEBUG', False) and getattr(settings, 'USE_MOCK_PROCESSOR', False):
                    from dochub.tasks.document_tasks import mock_process_document_task
                    mock_process_document_task.delay(str(instance.id))
                    logger.info(f"Using MOCK processor for document {instance.id} (development mode)")
                else:
                    # Use the full processing pipeline - use the already imported task
                    process_document_task.delay(str(instance.id))
            
        except Exception as e:
            logger.error(f"Error in document post-save signal handler: {str(e)}")
            
            # Update document status to error
            Document.objects.filter(id=instance.id).update(
                status='error',
                error_message=f"Error initializing document: {str(e)}"
            )

@receiver(pre_delete, sender=Document)
def handle_document_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for pre-delete events on Document model.
    Deletes the physical file when a document is deleted.
    
    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    if instance.file:
        file_path = instance.file.path
        if os.path.exists(file_path):
            try:
                # Delete the physical file
                os.remove(file_path)
                logger.info(f"Deleted file at: {file_path}")
                
                # Check if directory is empty and delete if necessary
                directory = os.path.dirname(file_path)
                if os.path.exists(directory) and not os.listdir(directory):
                    # Only delete if it's not the root Documents directory
                    if os.path.basename(directory) != "Documents":
                        os.rmdir(directory)
                        logger.info(f"Removed empty directory: {directory}")
                
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {str(e)}")

@receiver(post_save, sender=Folder)
def handle_folder_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save events on Folder model.
    Creates the physical directory for a new folder.
    
    Args:
        sender: The model class
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
    """
    if created:
        try:
            # Create physical directory
            physical_path = instance.physical_path
            os.makedirs(physical_path, exist_ok=True)
            logger.info(f"Created directory at: {physical_path}")
        except Exception as e:
            logger.error(f"Error creating folder directory: {str(e)}")

@receiver(pre_delete, sender=Folder)
def handle_folder_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for pre-delete events on Folder model.
    Deletes the physical directory and its contents when a folder is deleted.
    
    Args:
        sender: The model class
        instance: The actual instance being deleted
    """
    try:
        physical_path = instance.physical_path
        if os.path.exists(physical_path):
            # Make sure we're not deleting the root Documents directory
            if os.path.basename(physical_path) != "Documents":
                shutil.rmtree(physical_path)
                logger.info(f"Deleted directory at: {physical_path}")
            else:
                logger.warning(f"Prevented deleting root Documents directory")
    except Exception as e:
        logger.error(f"Error deleting folder directory: {str(e)}")

@receiver(pre_save, sender=Folder)
def handle_folder_pre_save(sender, instance, **kwargs):
    """
    Signal handler for pre-save events on Folder model.
    Handles folder renaming by renaming the physical directory.
    
    Args:
        sender: The model class
        instance: The actual instance being saved
    """
    if not instance.pk:
        return  # Skip for new folders (they'll be handled in post_save)
    
    try:
        # Get the old folder instance from the database
        old_folder = Folder.objects.get(pk=instance.pk)
        
        # Check if the name or parent has changed
        if old_folder.name != instance.name or old_folder.parent != instance.parent:
            old_path = old_folder.physical_path
            new_path = instance.physical_path
            
            # Only proceed if the old path exists
            if os.path.exists(old_path):
                # Create parent directory if it doesn't exist
                parent_dir = os.path.dirname(new_path)
                os.makedirs(parent_dir, exist_ok=True)
                
                # Rename directory
                shutil.move(old_path, new_path)
                logger.info(f"Renamed folder from {old_path} to {new_path}")
    except Folder.DoesNotExist:
        # This can happen if the folder is new
        pass
    except Exception as e:
        logger.error(f"Error in folder pre-save signal handler: {str(e)}")

def get_folder_physical_path(folder, use_new_name=False):
    """
    Get the physical path for a folder in the media directory.
    
    Args:
        folder: The Folder model instance
        use_new_name: Whether to use the instance's new name (for renames)
        
    Returns:
        String path to the folder's location in the filesystem
    """
    # Base media path where all folders will be stored
    media_root = settings.MEDIA_ROOT
    
    folder_path = build_folder_path(folder)
    
    # Join the media root with 'folders' directory and the folder path
    return os.path.join(media_root, 'folders', folder_path)