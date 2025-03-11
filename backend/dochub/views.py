# dochub/views.py

import logging
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Folder, Document
from .serializers import (
    FolderSerializer, 
    DocumentSerializer, 
    BulkUploadSerializer,
    BulkDeleteSerializer
)

logger = logging.getLogger(__name__)

class FolderViewSet(viewsets.ModelViewSet):
    """
    API endpoints for folder management.
    """
    serializer_class = FolderSerializer
    
    def get_queryset(self):
        """Get all folders, optionally filtered by parent."""
        queryset = Folder.objects.all()
        
        # Filter by parent folder if specified
        parent = self.request.query_params.get('parent', None)
        if parent:
            if parent.lower() == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent=parent)
        
        return queryset
    
    @action(detail=True)
    def documents(self, request, pk=None):
        """Get documents in a folder."""
        folder = self.get_object()
        documents = Document.objects.filter(folder=folder)
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True)
    def subfolders(self, request, pk=None):
        """Get subfolders of a folder."""
        folder = self.get_object()
        subfolders = Folder.objects.filter(parent=folder)
        serializer = FolderSerializer(subfolders, many=True)
        return Response(serializer.data)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoints for document management.
    """
    serializer_class = DocumentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def get_queryset(self):
        """Get all documents, optionally filtered by folder."""
        queryset = Document.objects.all()
        
        # Filter by folder if specified
        folder = self.request.query_params.get('folder', None)
        if folder:
            if folder.lower() == 'null' or folder.lower() == 'root':
                queryset = queryset.filter(folder__isnull=True)
            else:
                queryset = queryset.filter(folder=folder)
        
        return queryset
    
    def get_serializer_context(self):
        """Add request to serializer context for URL generation."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """
        Bulk upload multiple files at once.
        
        Request body should be form-data with:
        - files[]: Multiple file fields
        - folder: Optional folder ID
        """
        serializer = BulkUploadSerializer(data=request.data)
        if serializer.is_valid():
            documents = serializer.save()
            
            # Return the created documents
            doc_serializer = DocumentSerializer(
                documents, 
                many=True,
                context={'request': request}
            )
            return Response(
                {"message": f"Successfully uploaded {len(documents)} files", 
                 "documents": doc_serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkDeleteView(APIView):
    """
    API endpoint for bulk deleting folders and documents.
    """
    def post(self, request, format=None):
        """
        Bulk delete folders and documents.
        
        Request body should be JSON with:
        - folder_ids: List of folder IDs to delete
        - document_ids: List of document IDs to delete
        """
        serializer = BulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        folder_ids = serializer.validated_data.get('folder_ids', [])
        document_ids = serializer.validated_data.get('document_ids', [])
        
        deleted_folders = 0
        deleted_documents = 0
        
        with transaction.atomic():
            # Delete folders
            if folder_ids:
                folders_to_delete = Folder.objects.filter(id__in=folder_ids)
                deleted_folders = folders_to_delete.count()
                for folder in folders_to_delete:
                    logger.info(f"Deleting folder: {folder.id} - {folder.name}")
                folders_to_delete.delete()
            
            # Delete documents
            if document_ids:
                documents_to_delete = Document.objects.filter(id__in=document_ids)
                deleted_documents = documents_to_delete.count()
                for document in documents_to_delete:
                    logger.info(f"Deleting document: {document.id} - {document.name}")
                documents_to_delete.delete()
        
        return Response({
            "deleted_folders": deleted_folders,
            "deleted_documents": deleted_documents,
            "message": f"Successfully deleted {deleted_folders} folders and {deleted_documents} documents"
        })


@api_view(['GET'])
def document_graph(request, document_id):
    """Get knowledge graph for a document"""
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Placeholder for graph data
    graph_data = {
        "nodes": [],
        "relationships": []
    }
    
    return Response(graph_data)


@api_view(['GET'])
def folder_graph(request, folder_id):
    """Get knowledge graph for documents in a folder"""
    try:
        folder = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return Response({"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Placeholder for graph data
    graph_data = {
        "nodes": [],
        "relationships": []
    }
    
    return Response(graph_data)


@api_view(['GET'])
def entity_graph(request):
    """Get knowledge graph for a specific entity"""
    entity_name = request.query_params.get('name')
    entity_type = request.query_params.get('type')
    
    if not entity_name:
        return Response({"error": "Entity name is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Placeholder for graph data
    graph_data = {
        "nodes": [],
        "relationships": []
    }
    
    return Response(graph_data)