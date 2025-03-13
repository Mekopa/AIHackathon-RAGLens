# backend/dochub/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FolderViewSet, 
    DocumentViewSet, 
    BulkDeleteView,
    document_graph,
    folder_graph,
    entity_graph,
    document_status
)

# Create a router and register viewsets
router = DefaultRouter()
router.register('folders', FolderViewSet, basename='folder')
router.register('documents', DocumentViewSet, basename='document')

# URL patterns
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Bulk operations
    path('bulk_delete/', BulkDeleteView.as_view(), name='bulk-delete'),
    
    # Graph-related endpoints
    path('graph/document/<uuid:document_id>/', document_graph, name='document-graph'),
    path('graph/folder/<uuid:folder_id>/', folder_graph, name='folder-graph'),
    path('graph/entity/', entity_graph, name='entity-graph'),
    path('documents/status/<uuid:document_id>/', document_status, name='document-status'),
    path('documents/status/', document_status, name='documents-status'),
]