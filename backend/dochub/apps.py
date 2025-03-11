# dochub/apps.py

from django.apps import AppConfig
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class DochubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dochub'
    
    def ready(self):
        """
        Register signal handlers and create initial data when the app is ready.
        """
        import dochub.signals  # Import signals to register handlers
        
        # Don't run initialization during migrations or other management commands
        import sys
        if 'runserver' in sys.argv or 'uvicorn' in sys.argv or 'daphne' in sys.argv:
            # Use try/except to avoid issues if this runs before migrations
            try:
                self.ensure_media_structure()
            except Exception as e:
                logger.error(f"Error creating initial media structure: {e}")
    
    def ensure_media_structure(self):
        """Ensure the media structure exists."""
        # Create the media root if it doesn't exist
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # Create Documents root directory
        documents_root = os.path.join(settings.MEDIA_ROOT, 'Documents')
        if not os.path.exists(documents_root):
            os.makedirs(documents_root)
            logger.info(f"Created Documents root directory at: {documents_root}")
        
        # Create root folder in database
        from .models import Folder
        
        # Try to find or create the Documents root folder
        root_folder, created = Folder.objects.get_or_create(
            name="Documents",
            parent=None,
            defaults={
                'name': 'Documents',
                'parent': None
            }
        )
        
        if created:
            logger.info(f"Created root folder 'Documents' with ID: {root_folder.id}")
        else:
            logger.info(f"Root folder 'Documents' already exists with ID: {root_folder.id}")