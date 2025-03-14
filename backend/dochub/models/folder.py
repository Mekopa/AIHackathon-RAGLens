# backend/dochub/models/folder.py

import uuid
import os
from django.db import models
from django.conf import settings

def build_folder_path(folder):
    """
    Recursively build the folder path based on hierarchy.
    Always starts with Documents/
    
    Args:
        folder: Folder instance
        
    Returns:
        str: Path for the folder (e.g., "Documents/FolderA/SubfolderB")
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

class Folder(models.Model):
    """Folder model for organizing documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subfolders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """String representation of the folder"""
        return self.name
    
    class Meta:
        """Meta options for the Folder model"""
        ordering = ['name']
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
    
    @property
    def path(self):
        """Get the full path of the folder"""
        return build_folder_path(self)
    
    @property
    def document_count(self):
        """Get the number of documents in this folder"""
        return self.documents.count()
    
    @property
    def subfolder_count(self):
        """Get the number of subfolders in this folder"""
        return self.subfolders.count()
    
    @property
    def physical_path(self):
        """Get the physical path in the filesystem"""
        return os.path.join(settings.MEDIA_ROOT, self.path)
    
    def create_physical_folder(self):
        """Create the physical folder in the filesystem"""
        os.makedirs(self.physical_path, exist_ok=True)
        return self.physical_path
    
    def get_ancestors(self):
        """Get all ancestor folders"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
    
    def get_descendants(self):
        """Get all descendant folders (recursively)"""
        descendants = list(self.subfolders.all())
        for child in self.subfolders.all():
            descendants.extend(child.get_descendants())
        return descendants