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
    metadata = models.JSONField(default=dict, blank=True) 
    class Meta:
        ordering = ['-last_interaction']  
        db_table = 'profiler_chat_sessions'


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
        db_table = 'profiler_chat_messages'

class RawUserInput(models.Model):
    session = models.ForeignKey(
        ChatSession,
        related_name="raw_inputs",
        on_delete=models.CASCADE
    )

    input_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text"),
            ("json", "JSON"),
            ("pdf", "PDF"),
            ("docx", "DOCX"),
        ]
    )

    raw_text = models.TextField(blank=True, null=True)
    raw_file = models.FileField(upload_to="raw_uploads/", blank=True, null=True)

    user_prompt = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']  
        db_table = 'profiler_raw_user_inputs'
class NormalizedContext(models.Model):
    session = models.ForeignKey(
        ChatSession,
        related_name="contexts",
        on_delete=models.CASCADE
    )

    source_input = models.ForeignKey(
        RawUserInput,
        related_name="normalized_versions",
        on_delete=models.CASCADE
    )

    extracted_text = models.TextField()
    content_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']  
        db_table = 'profiler_normalized_contexts'
class ProfilingInference(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)

    profile_subject = models.CharField(max_length=255)
    inferred_domain = models.CharField(max_length=255, blank=True, null=True)

    key_attributes = models.JSONField(default=list, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    limitations = models.JSONField(default=list, blank=True)
    risks_or_gaps = models.JSONField(default=list, blank=True)
    notable_observations = models.JSONField(default=list, blank=True)

    confidence_score = models.FloatField(default=0.0)

    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']  
        db_table = 'profiler_profiling_inferences'
class GeneratedOutput(models.Model):
    session = models.ForeignKey(
        ChatSession,
        related_name="outputs",
        on_delete=models.CASCADE
    )

    output_type = models.CharField(
        max_length=20,
        choices=[
            ("chat", "Chat"),
            ("pdf", "PDF"),
            ("docx", "DOCX"),
        ]
    )

    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="generated_outputs/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']  
        db_table = 'profiler_generated_outputs'

