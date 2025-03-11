# chatbot/views.py

from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer

class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for ChatSession model"""
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        return ChatSession.objects.all()

class ChatMessageListCreate(generics.ListCreateAPIView):
    """List and create chat messages"""
    serializer_class = ChatMessageSerializer
    
    def get_queryset(self):
        session_id = self.kwargs.get('session_id')
        return ChatMessage.objects.filter(session_id=session_id)
    
    def create(self, request, *args, **kwargs):
        session_id = self.kwargs.get('session_id')
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Chat session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create user message
        serializer = self.get_serializer(data={
            **request.data,
            "role": "user",
            "session": session_id
        })
        serializer.is_valid(raise_exception=True)
        user_message = serializer.save()
        
        # In a real implementation, this would call the RAG pipeline to generate a response
        # For now, just create a placeholder assistant message
        assistant_message = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content="This is a placeholder response. The RAG system will be implemented soon."
        )
        
        # Return both messages
        return Response({
            "user_message": self.get_serializer(user_message).data,
            "assistant_message": self.get_serializer(assistant_message).data
        }, status=status.HTTP_201_CREATED)
