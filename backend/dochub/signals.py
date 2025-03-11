# dochub/signals.py

import os
import logging
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from .models import Document, Folder, build_folder_path
from .tasks import process_document_task

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Folder)
def handle_folder_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save events on Folder model.
    Creates the physical directory for a new folder.
    """
    if created:
        # Get the physical path - this should always be under Documents/
        folder_physical_path = os.path.join(settings.MEDIA_ROOT, build_folder_path(instance))
        
        try:
            # Create the directory
            os.makedirs(folder_physical_path, exist_ok=True)
            logger.debug(f"Created directory at: {folder_physical_path}")
        except Exception as e:
            logger.error(f"Error creating folder directory {folder_physical_path}: {e}")

@receiver(pre_delete, sender=Document)
def handle_document_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for pre-delete events on Document model.
    Deletes the physical file when a document is deleted.
    """
    if instance.file:
        file_path = instance.file.path
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file at: {file_path}")
                
                # Clean up empty directory if it exists
                dir_path = os.path.dirname(file_path)
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    logger.info(f"Removed empty directory: {dir_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")

@receiver(post_save, sender=Folder)
def handle_folder_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save events on Folder model.
    Creates the physical directory for a new folder.
    """
    if created:
        folder_physical_path = os.path.join(settings.MEDIA_ROOT, build_folder_path(instance))
        
        try:
            # Create the directory
            os.makedirs(folder_physical_path, exist_ok=True)
            logger.debug(f"Created directory at: {folder_physical_path}")
        except Exception as e:
            logger.error(f"Error creating folder directory {folder_physical_path}: {e}")

@receiver(pre_delete, sender=Folder)
def handle_folder_pre_delete(sender, instance, **kwargs):
    """
    Signal handler for pre-delete events on Folder model.
    Deletes the physical directory when a folder is deleted.
    """
    folder_physical_path = get_folder_physical_path(instance)
    
    if os.path.exists(folder_physical_path):
        try:
            shutil.rmtree(folder_physical_path)
            logger.info(f"Deleted directory at: {folder_physical_path}")
        except Exception as e:
            logger.error(f"Error deleting folder directory {folder_physical_path}: {e}")

@receiver(pre_save, sender=Folder)
def handle_folder_pre_save(sender, instance, **kwargs):
    """
    Signal handler for pre-save events on Folder model.
    Handles folder renaming by renaming the physical directory.
    """
    if not instance.pk:
        return  # Skip for new folders
    
    try:
        old_folder = Folder.objects.get(pk=instance.pk)
        if old_folder.name != instance.name:
            old_path = get_folder_physical_path(old_folder)
            new_path = get_folder_physical_path(instance, use_new_name=True)
            
            if os.path.exists(old_path):
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                # Move the directory
                shutil.move(old_path, new_path)
                logger.info(f"Renamed folder from {old_path} to {new_path}")
    except Folder.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling folder rename: {e}")

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