# dochub/models.py

import uuid
from django.db import models
import os

def build_folder_path(folder):
    """
    Recursively build the folder path based on hierarchy.
    Always starts with Documents/
    """
    parts = []
    current = folder
    
    # Build path starting from the deepest folder
    while current:
        parts.insert(0, current.name)
        current = current.parent
    
    # Ensure it starts with Documents if not already
    if not parts or parts[0] != "Documents":
        parts.insert(0, "Documents")
        
    return os.path.join(*parts)

def document_upload_path(instance, filename):
    """
    Define upload path for documents within the Documents directory.
    For root level: media/Documents/filename
    For folders: media/Documents/FolderName/filename
    """
    if instance.folder:
        # Get folder path
        folder_path = build_folder_path(instance.folder)
        return os.path.join(folder_path, filename)
    else:
        # Root level document goes directly in Documents folder
        return os.path.join("Documents", filename)

class Folder(models.Model):
    """Folder model for organizing documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, 
                              null=True, blank=True, related_name='subfolders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def path(self):
        """Get the full path of the folder"""
        return build_folder_path(self)
    
    class Meta:
        ordering = ['name']

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
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, 
                              null=True, blank=True, related_name='documents')
    file_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']