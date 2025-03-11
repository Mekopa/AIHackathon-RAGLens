#chatbot/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.ChatSessionViewSet, basename='chat-session')

urlpatterns = [
    path('sessions/<uuid:session_id>/messages/', views.ChatMessageListCreate.as_view(), name='chat-messages'),
]

urlpatterns += router.urls