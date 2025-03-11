#dochub/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import Folder, Document
from .serializers import FolderSerializer, DocumentSerializer

class FolderViewSet(viewsets.ModelViewSet):
    """ViewSet for Folder model"""
    serializer_class = FolderSerializer
    
    def get_queryset(self):
        return Folder.objects.all()

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document model"""
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        return Document.objects.all()
    
    def perform_create(self, serializer):
        """Process document after creation"""
        document = serializer.save()
        # In the real implementation, we would call the document processing task here
        # For now, we'll just update the status to 'ready'
        document.status = 'ready'
        document.save()

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
