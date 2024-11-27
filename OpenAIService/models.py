from django.db import models
from .enums import Assistant
import uuid

# Create your models here.
class OpenAIAssistant(models.Model):
    assistant_id = models.CharField(max_length=500,blank=False)
    name = models.CharField(max_length=50, choices=[(assistant.name, assistant.role_details['name']) for assistant in Assistant])
    instructions = models.TextField(blank=False) 
    open_ai_model = models.CharField(max_length=500,blank=False)
    tools = models.JSONField(default=list,blank=False)



class Tool(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tool_code = models.TextField()
    default_values_for_non_llm_params = models.JSONField(default=dict,blank=True)
    tool_json_spec = models.JSONField(default=dict,blank=True)
    name = models.CharField(max_length=100)
    context_params = models.JSONField(default=list, blank=True)
    def __str__(self):
        return self.name



class PromptTemplate(models.Model):
    ASSISTANT = 'assistant'
    RAG = 'rag'

    LLM_MODE_CHOICES = [
        (ASSISTANT, 'Assistant'),
        (RAG, 'Our RAG Implementation')
    ]

    name = models.CharField(max_length=100)
    llm_config_name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, blank=True, null=True)
    required_kwargs = models.JSONField(blank=True,default=list, help_text="Required key words to be passed in user prompt template. If not provided by calling code, error will be raised. AS OF NOW, ERROR IS RAISED IF ANY KEYWORD IS MISSED, SINCE OTHERWISE $TEMPLATE_VAR LIKE THING WILL REMAIN IN PROMPT. FOR REQUIRED_KEYWORD ARGUMENTS FUNCTIONALITY, WE NEED DEFAULT VALUES OF OPTIONAL ARGS. CHECK IF THIS IS NEEDED, OR REMOVE REQUIRED KWARGS FIELD FROM HERE.")
    initial_messages_templates = models.JSONField(blank=True,default=list,help_text="Initial msgs in the format [{'role': 'assistant|user', 'content': '...'}]")
    system_prompt_template = models.TextField()
    user_prompt_template = models.TextField(blank=True, default="")
    logged_context_vars = models.JSONField(blank=True,default=list, help_text="Context variables to be logged in the chat log along with each user message, for later analysis.")
    tools = models.ManyToManyField(Tool,blank=True)
    streaming_enabled = models.BooleanField(default=False)
    llm_mode = models.CharField(max_length=10, choices=LLM_MODE_CHOICES, default=RAG)


class ChatHistory(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    chat_history = models.JSONField(default=list)
    current_context_variables = models.JSONField(default=dict)
    chat_id =models.UUIDField(default=uuid.uuid4, editable=False,unique=True)
    thread_id = models.CharField(max_length=100,blank=True, null=True)


class KnowledgeRepository(models.Model):
    class SourceType(models.IntegerChoices):
        AZURE_BLOB = 1, "Azure Blob"
        AMAZON_S3 = 2, "Amazon S3"
        GOOGLE_DRIVE = 3, "Google Drive"
    
    class TypeOfRepo(models.IntegerChoices):
        COURSE = 1, "Course"

    type_of_repo =  models.IntegerField(choices=TypeOfRepo.choices)  
    #organization = models.ForeignKey(Organization, on_delete=models.CASCADE, to_field='id')
    #api_key = models.CharField(max_length=255, blank=True)  
    #course_id = models.ForeignKey(Course, on_delete=models.CASCADE, to_field='id')
    source_path = models.CharField(max_length=255) 
    source_type = models.IntegerField(choices=SourceType.choices) 
    index_path = models.CharField(max_length=255, blank=True) 
    sas_token = models.CharField(max_length=255, blank=True)
    assistant_id=models.ForeignKey(OpenAIAssistant, on_delete=models.CASCADE, to_field='id', blank=True, null=True) 
    


class ContentReference(models.Model):
    class ContentType(models.TextChoices):
        PDF = 1, "PDF"
        YOUTUBE_VIDEO = 2, "YouTube Video"

    content_type = models.IntegerField(choices=ContentType.choices)
    #course_id = models.ForeignKey(Course, on_delete=models.CASCADE, to_field='id')
    path = models.CharField(max_length=255)  
    knowledge_repository_id = models.ForeignKey('KnowledgeRepository', on_delete=models.CASCADE, to_field='id')
    title=models.CharField(max_length=255,null=True)  
    file_id=models.CharField(max_length=255,null=True)  
    class Meta:
        unique_together = ('knowledge_repository_id', 'path')