from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    """
    Stores implicit session data and system-level signals.
    """
    session_id = models.CharField(max_length=255, unique=True)
    detected_domain = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True) # For implicit signals

    def __str__(self):
        return f"Session {self.session_id} - {self.detected_domain}"

class ChatMessage(models.Model):
    """
    Stores the actual conversation history for the AI's memory.
    """
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']