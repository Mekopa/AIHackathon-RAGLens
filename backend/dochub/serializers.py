#dochub/serializers.py

from rest_framework import serializers
from .models import Folder, Document

class FolderSerializer(serializers.ModelSerializer):
    """Serializer for Folder model"""
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'created_at', 'updated_at']

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    class Meta:
        model = Document
        fields = ['id', 'name', 'file', 'folder', 'file_type', 'size', 
                  'status', 'error_message', 'created_at', 'updated_at']
        read_only_fields = ['file_type', 'size', 'status', 'error_message']