# backend/dochub/api/views.py

import logging
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404

from ..models import Folder, Document
from .serializers import (
    FolderSerializer, 
    DocumentSerializer, 
    BulkUploadSerializer,
    BulkDeleteSerializer
)
from ..pipeline.graphs.client import Neo4jClient
from ..utils.graph_visualizer import GraphVisualizer

logger = logging.getLogger(__name__)

@api_view(['GET'])
def document_status(request, document_id=None):
    """
    Get status for a single document or multiple documents
    
    GET /api/dochub/documents/status/{document_id}/ - Get status for a single document
    GET /api/dochub/documents/status/?ids=id1,id2,id3 - Get status for multiple documents
    """
    try:
        # Handle multiple document IDs in query parameter
        if document_id is None and 'ids' in request.query_params:
            document_ids = request.query_params.get('ids', '').split(',')
            document_ids = [doc_id.strip() for doc_id in document_ids if doc_id.strip()]
            
            if not document_ids:
                return Response(
                    {"error": "No document IDs provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get status for multiple documents
            documents = Document.objects.filter(id__in=document_ids).values(
                'id', 'name', 'status', 'error_message', 'updated_at'
            )
            
            # Create a dictionary of document statuses
            status_map = {
                str(doc['id']): {
                    'id': str(doc['id']),
                    'name': doc['name'],
                    'status': doc['status'],
                    'error': doc['error_message'],
                    'updated_at': doc['updated_at'].isoformat() if doc['updated_at'] else None
                }
                for doc in documents
            }
            
            # Add missing IDs with 'not_found' status
            for doc_id in document_ids:
                if doc_id not in status_map:
                    status_map[doc_id] = {
                        'id': doc_id,
                        'status': 'not_found'
                    }
            
            return Response(status_map)
        
        # Handle single document ID in URL
        elif document_id is not None:
            try:
                document = Document.objects.get(id=document_id)
                return Response({
                    'id': str(document.id),
                    'name': document.name,
                    'status': document.status,
                    'error': document.error_message,
                    'updated_at': document.updated_at.isoformat() if document.updated_at else None
                })
            except Document.DoesNotExist:
                return Response(
                    {"error": f"Document {document_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # No document ID provided
        else:
            return Response(
                {"error": "Document ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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


def document_graph(request, document_id):
    """Get knowledge graph for a document"""
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Initialize Neo4j client
        neo4j_client = Neo4jClient()
        
        # Retrieve graph data
        graph_records = neo4j_client.get_document_graph(document_id)
        
        # Process records into JSON-compatible format
        nodes = {}
        relationships = {}
        
        for record in graph_records:
            # Extract path data
            path = record["path"]
            
            # Process nodes
            for node in path.nodes:
                if node.id not in nodes:
                    nodes[node.id] = {
                        "id": str(node.id),
                        "labels": list(node.labels),
                        "properties": dict(node)
                    }
            
            # Process relationships
            for rel in path.relationships:
                if rel.id not in relationships:
                    relationships[rel.id] = {
                        "id": str(rel.id),
                        "type": rel.type,
                        "start_node": str(rel.start_node.id),
                        "end_node": str(rel.end_node.id),
                        "properties": dict(rel)
                    }
        
        # Use the GraphVisualizer to format the data
        raw_graph_data = {
            "nodes": list(nodes.values()),
            "relationships": list(relationships.values())
        }
        
        # Check if we need 2D or 3D format
        format_type = request.query_params.get('format', '2d').lower()
        
        # Process using GraphVisualizer
        processed_data = GraphVisualizer.process_neo4j_graph(
            raw_graph_data["nodes"], 
            raw_graph_data["relationships"]
        )
        
        # Convert to appropriate format for react-force-graph
        if format_type == '3d':
            graph_data = GraphVisualizer.to_force_graph_3d_format(processed_data)
        else:
            graph_data = GraphVisualizer.to_force_graph_format(processed_data)
        
        return Response(graph_data)
        
    except Exception as e:
        logger.error(f"Error retrieving graph data: {e}")
        return Response(
            {"error": "Failed to retrieve graph data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def folder_graph(request, folder_id):
    """Get knowledge graph for documents in a folder"""
    try:
        folder = Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return Response({"error": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Initialize Neo4j client
        neo4j_client = Neo4jClient()
        
        # Retrieve graph data
        graph_records = neo4j_client.get_folder_graph(folder_id=folder_id)
        
        # Process records into JSON-compatible format
        nodes = {}
        relationships = {}
        
        for record in graph_records:
            # Extract path data
            path = record["path"]
            
            # Process nodes
            for node in path.nodes:
                if node.id not in nodes:
                    nodes[node.id] = {
                        "id": str(node.id),
                        "labels": list(node.labels),
                        "properties": dict(node)
                    }
            
            # Process relationships
            for rel in path.relationships:
                if rel.id not in relationships:
                    relationships[rel.id] = {
                        "id": str(rel.id),
                        "type": rel.type,
                        "start_node": str(rel.start_node.id),
                        "end_node": str(rel.end_node.id),
                        "properties": dict(rel)
                    }
        
        # Use the GraphVisualizer to format the data
        raw_graph_data = {
            "nodes": list(nodes.values()),
            "relationships": list(relationships.values())
        }
        
        # Check if we need 2D or 3D format
        format_type = request.query_params.get('format', '2d').lower()
        
        # Process using GraphVisualizer
        processed_data = GraphVisualizer.process_neo4j_graph(
            raw_graph_data["nodes"], 
            raw_graph_data["relationships"]
        )
        
        # Convert to appropriate format for react-force-graph
        if format_type == '3d':
            graph_data = GraphVisualizer.to_force_graph_3d_format(processed_data)
        else:
            graph_data = GraphVisualizer.to_force_graph_format(processed_data)
            
        # Add folder information to the response
        graph_data["folder"] = {
            "id": str(folder.id),
            "name": folder.name,
            "document_count": Document.objects.filter(folder=folder).count()
        }
        
        return Response(graph_data)
        
    except Exception as e:
        logger.error(f"Error retrieving folder graph data: {e}")
        return Response(
            {"error": "Failed to retrieve folder graph data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def entity_graph(request):
    """Get knowledge graph for a specific entity"""
    entity_name = request.query_params.get('name')
    entity_type = request.query_params.get('type')
    
    if not entity_name:
        return Response({"error": "Entity name is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Initialize Neo4j client
        neo4j_client = Neo4jClient()
        
        # Retrieve graph data
        graph_records = neo4j_client.get_entity_relationships(entity_name, entity_type)
        
        # Process records into JSON-compatible format
        nodes = {}
        relationships = {}
        
        for record in graph_records:
            # Extract entities and relationship
            entity = record["e"]
            relation = record["r"]
            related = record["related"]
            
            # Process entity node
            entity_id = entity.id
            if entity_id not in nodes:
                nodes[entity_id] = {
                    "id": str(entity_id),
                    "labels": list(entity.labels),
                    "properties": dict(entity)
                }
            
            # Process related node
            related_id = related.id
            if related_id not in nodes:
                nodes[related_id] = {
                    "id": str(related_id),
                    "labels": list(related.labels),
                    "properties": dict(related)
                }
            
            # Process relationship
            rel_id = relation.id
            if rel_id not in relationships:
                relationships[rel_id] = {
                    "id": str(rel_id),
                    "type": relation.type,
                    "start_node": str(relation.start_node.id),
                    "end_node": str(relation.end_node.id),
                    "properties": dict(relation)
                }
        
        # Use the GraphVisualizer to format the data
        raw_graph_data = {
            "nodes": list(nodes.values()),
            "relationships": list(relationships.values())
        }
        
        # Check if we need 2D or 3D format
        format_type = request.query_params.get('format', '2d').lower()
        
        # Process using GraphVisualizer
        processed_data = GraphVisualizer.process_neo4j_graph(
            raw_graph_data["nodes"], 
            raw_graph_data["relationships"]
        )
        
        # Convert to appropriate format for react-force-graph
        if format_type == '3d':
            graph_data = GraphVisualizer.to_force_graph_3d_format(processed_data)
        else:
            graph_data = GraphVisualizer.to_force_graph_format(processed_data)
            
        # Add entity information to the response
        graph_data["entity"] = {
            "name": entity_name,
            "type": entity_type,
            "node_count": len(nodes),
            "relationship_count": len(relationships)
        }
        
        return Response(graph_data)
        
    except Exception as e:
        logger.error(f"Error retrieving entity graph data: {e}")
        return Response(
            {"error": "Failed to retrieve entity graph data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )