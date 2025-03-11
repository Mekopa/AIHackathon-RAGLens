# dochub/serializers.py

from rest_framework import serializers
from .models import Folder, Document

class FolderSerializer(serializers.ModelSerializer):
    """Serializer for Folder model"""
    document_count = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'created_at', 'updated_at', 
                  'document_count', 'subfolder_count']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_count(self, obj):
        """Get count of documents in this folder"""
        return obj.documents.count()
    
    def get_subfolder_count(self, obj):
        """Get count of subfolders"""
        return obj.subfolders.count()
    
    def validate_name(self, value):
        """Validate folder name uniqueness within a parent folder"""
        parent = self.initial_data.get('parent')
        
        # Check if a folder with this name already exists in the same parent
        if Folder.objects.filter(name=value, parent=parent).exists():
            if self.instance and self.instance.name == value and str(self.instance.parent_id) == str(parent):
                # Allow updating the same folder without changing name
                return value
            raise serializers.ValidationError("A folder with this name already exists in this location")
        return value

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = ['id', 'name', 'file', 'url', 'folder', 'file_type', 'size', 
                  'status', 'error_message', 'created_at', 'updated_at']
        read_only_fields = ['file_type', 'size', 'status', 'error_message', 
                            'created_at', 'updated_at']
    
    def get_url(self, obj):
        """Get download URL for the document"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def validate_name(self, value):
        """Validate document name uniqueness within a folder"""
        folder = self.initial_data.get('folder')
        
        # Check if a document with this name already exists in the same folder
        if Document.objects.filter(name=value, folder=folder).exists():
            if self.instance and self.instance.name == value and str(self.instance.folder_id) == str(folder):
                # Allow updating the same document without changing name
                return value
            raise serializers.ValidationError("A document with this name already exists in this folder")
        return value

class BulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk uploading files"""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        write_only=True
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        allow_null=True,
        required=False
    )

    def create(self, validated_data):
        files = validated_data.pop('files')
        folder = validated_data.get('folder')
        
        documents = []
        for file in files:
            # Create a new document for each file
            document = Document(
                name=file.name,
                file=file,
                folder=folder,
                status='processing'  # Initial status
            )
            document.save()  # Save to trigger signal for processing
            documents.append(document)
        
        return documents

class BulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk deleting files and folders"""
    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )

    def validate(self, attrs):
        """Ensure at least one list has items"""
        folder_ids = attrs.get('folder_ids', [])
        document_ids = attrs.get('document_ids', [])
        
        if not folder_ids and not document_ids:
            raise serializers.ValidationError(
                "At least one of 'folder_ids' or 'document_ids' must be provided."
            )
        
        return attrs