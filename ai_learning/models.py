from django.db import models

class PromptTemplates(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    prompt = models.TextField(help_text="actual prompt with variables")
    additional_guardrail_prompt = models.TextField(default="",help_text="additional prompt text to be added at end of each user msg for "
                                                "additional guardrails. (This won't be saved in conversation history)")
    type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'ai_learning'


class Video(models.Model):
    video_id = models.CharField(max_length=100, primary_key=True)
    url = models.URLField()
    title = models.CharField(max_length=100)
    transcript = models.TextField()
    thumbnail = models.URLField(default="")
    timestamped_transcript = models.TextField(default="")
    chapters_data = models.JSONField(default=dict)
    questions_data = models.JSONField(default=dict)
    duration = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        app_label = 'ai_learning'
    
    
class UserConsumedVideos(models.Model):
    user_id = models.CharField(max_length=100)
    video_id = models.ForeignKey(Video, on_delete=models.DO_NOTHING, to_field='video_id')
    chapters_data = models.JSONField(default=dict)
    questions_data = models.JSONField(default=dict) 
    time_spent = models.IntegerField(default=0)
    quizzes_attempted = models.IntegerField(default=0)  
    total_points_scored = models.IntegerField(default=0)
    highlights = models.JSONField(default=dict)
    chat_history = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    chat_count = models.IntegerField(default=0)
    class Meta:
        unique_together = ('user_id', 'video_id')
        app_label = 'ai_learning'
        
