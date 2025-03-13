# dochub/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'folders', views.FolderViewSet, basename='folder')
router.register(r'documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    # Graph-related endpoints
    path('graph/document/<uuid:document_id>/', views.document_graph, name='document-graph'),
    path('graph/folder/<uuid:folder_id>/', views.folder_graph, name='folder-graph'),
    path('graph/entity/', views.entity_graph, name='entity-graph'),
    
    # Bulk operations
    path('bulk_delete/', views.BulkDeleteView.as_view(), name='bulk-delete'),
    
    # Debug dashboard
    path('debug/dashboard/', views.test_dashboard, name='test-dashboard'),
    path('documents/<uuid:document_id>/logs/', views.document_logs, name='document-logs'),
    path('documents/<uuid:document_id>/chunks/', views.document_chunks, name='document-chunks'),
    
    # Include router URLs
    path('', include(router.urls)),
]