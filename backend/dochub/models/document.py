# backend/dochub/models/document.py

import uuid
import os
from django.db import models
from .folder import Folder, build_folder_path

def document_upload_path(instance, filename):
    """
    Define upload path for documents.
    
    For root level: media/Documents/filename
    For folders: media/Documents/FolderPath/filename
    
    Args:
        instance: Document instance
        filename: Original filename
        
    Returns:
        str: Path where the file should be stored
    """
    if instance.folder:
        # Get folder path
        folder_path = build_folder_path(instance.folder)
        return os.path.join(folder_path, filename)
    else:
        # Root level document goes directly in Documents folder
        return os.path.join("Documents", filename)

class Document(models.Model):
    """Document model for storing files"""
    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    folder = models.ForeignKey(
        Folder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='documents'
    )
    file_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='processing'
    )
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        """String representation of the document"""
        return self.name
    
    class Meta:
        """Meta options for the Document model"""
        ordering = ['-created_at']
        verbose_name = "Document"
        verbose_name_plural = "Documents"
    
    @property
    def is_processed(self):
        """Check if document has been processed"""
        return self.status == 'ready'
    
    @property
    def extension(self):
        """Get file extension"""
        return os.path.splitext(self.name)[1][1:].lower() if '.' in self.name else ''
    
    @property
    def path(self):
        """Get the full path of the document"""
        if not self.file:
            return None
        return self.file.path
    
    @property
    def folder_path(self):
        """Get the folder path for the document"""
        if self.folder:
            return build_folder_path(self.folder)
        return "Documents"