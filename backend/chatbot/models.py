#chatbot/models.py

import uuid
from django.db import models
from dochub.models import Document

class ChatSession(models.Model):
    """Chat session model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    """Chat message model"""
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    class Meta:
        ordering = ['created_at']

class DocumentReference(models.Model):
    """References to documents used in chat messages"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='document_references')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    relevance_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reference to {self.document.name} in message {self.message.id}"
