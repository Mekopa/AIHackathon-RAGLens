#chatbot/serializers.py

from rest_framework import serializers
from .models import ChatSession, ChatMessage, DocumentReference

class DocumentReferenceSerializer(serializers.ModelSerializer):
    """Serializer for DocumentReference model"""
    document_name = serializers.ReadOnlyField(source='document.name')
    
    class Meta:
        model = DocumentReference
        fields = ['id', 'document', 'document_name', 'relevance_score']

class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    document_references = DocumentReferenceSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at', 'document_references']
        read_only_fields = ['created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['created_at', 'updated_at']