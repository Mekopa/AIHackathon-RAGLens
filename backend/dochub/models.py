#dochub/models.py

import uuid
from django.db import models
from django.utils.text import slugify
import os

def document_upload_path(instance, filename):
    """Define upload path for documents"""
    # Format: documents/<document_id>/<filename>
    return os.path.join('documents', str(instance.id), filename)

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
        if self.parent:
            return f"{self.parent.path}/{self.name}"
        return self.name

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

    def save(self, *args, **kwargs):
        # Set file_type based on file extension
        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            self.file_type = ext[1:] if ext else ''  # Remove the dot from extension
            
            # Update file size if available
            if self.file.size:
                self.size = self.file.file.size
                
        super().save(*args, **kwargs)
