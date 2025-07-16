import os
import uuid
import typing

from OpenAIService.models import ChatHistory
from common.models import TimeStampedModel
from django.db import models, transaction
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

class UserAttemptResponseEvaluation(TimeStampedModel):
    """
    This model is used to store the evaluations of the practice question attempted by the user.
    """

    class Status(models.IntegerChoices):
        PARTIAL = 1
        COMPLETE = 2
        ERROR = 3

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True,
                          help_text=_("Unique ID"))
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                help_text=_("Cummulative score of evaluation"))

    fluency = models.CharField(max_length=32, null=True, blank=True,
                               help_text=_("Fluency score"))
    fluency_details = models.JSONField(null=True, blank=True,
                                       help_text=_("Additional fluency evaluation data"))

    pronunciation = models.CharField(max_length=32, null=True, blank=True,
                                     help_text=_("Pronunciation score"))
    pronunciation_details = models.JSONField(null=True, blank=True,
                                             help_text=_("Additional pronunciation evaluation data"))

    coherence = models.CharField(max_length=32, null=True, blank=True,
                                 help_text=_("Coherence score"))
    coherence_details = models.JSONField(null=True, blank=True,
                                         help_text=_("Additional coherence evaluation data"))

    grammar = models.CharField(max_length=32, null=True, blank=True,
                               help_text=_("Grammar score"))
    grammar_details = models.JSONField(null=True, blank=True,
                                       help_text=_("Additional Grammar evaluation data"))

    vocab = models.CharField(max_length=32, null=True, blank=True,
                             help_text=_("Vocab score"))
    vocab_details = models.JSONField(null=True, blank=True,
                                     help_text=_("Additional vocab evaluation data"))
    
    sentiment = models.CharField(max_length=32, null=True, blank=True,
                             help_text=_("Sentiment score"))
    sentiment_details = models.JSONField(null=True, blank=True,
                                     help_text=_("Additional sentiment evaluation data"))

    summary = models.JSONField(null=True, blank=True,
                                       help_text=_("Any additional metadata related to the evaluation"))

    status = models.IntegerField(choices=Status.choices, default=Status.PARTIAL)

    ideal_response_details = models.JSONField(null=True, blank=True,
                                       help_text=_("Metadata for ideal response"))

    class Meta:
        verbose_name = _("User Attempt Response Evaluation")
        verbose_name_plural = _("User Attempt Response Evaluations")

    @cached_property
    def transscript_url(self):
        url = f"{self.id}/transcription_data/transcript.txt"
        return url

    @property
    def status_string(self):
        return self.Status(self.status).label

class EventFlow(TimeStampedModel):

    class Status(models.IntegerChoices):
        STARTED = 1
        COMPLETED = 2
        ERROR = 3
        ABORTED = 4

    TERMINATION_STATES = (Status.ERROR, Status.ABORTED)

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True,
                          help_text=_("Unique ID"))

    type = models.CharField(max_length=24, null=False, blank=False)

    root_arguments = models.JSONField(null=True, blank=True,
                               help_text=_("Arguments passed in while starting the event flow."))
    status = models.IntegerField(choices=Status.choices, default=Status.STARTED)

    initiated_by = models.CharField(max_length=64, editable=False, 
                                    help_text=_("Id of the initiator event/person"))
    
    run_duration = models.DurationField('Run duration', null=True, blank=True)

    start_time = models.DateTimeField('Start time of event flow', null=True, blank=True, auto_now_add=True)

    end_time = models.DateTimeField('Start time of event flow', null=True, blank=True)
    

    @property
    def are_all_processors_complete(self):
        return not self.processors.exclude(status=
                                       EventFlowProcessorState.Status.COMPLETED)
    
    def check_if_given_processors_are_done(self, *, processor_names: typing.List[str]) -> bool:
        return not self.processors.exclude(status__in=
                                       EventFlowProcessorState.COMPLETION_STATES).filter(processor_name__in=
                                                                                        processor_names).exists()
    
    def get_summarized_status(self):
        processor_states = self.processors.distinct(
            'processor_name'
            ).in_bulk(field_name='processor_name')

        summarized_result = ""
        
        for processor_name, state in processor_states.items():
            status = state.get_status_display()
            summarized_result += f"{processor_name:25s}:{status}:{state.run_duration}\n"
        return summarized_result
    
    def get_processor_result(self, processor_name):
        return self.processors.get(processor_name=processor_name).result
    
    def get_processor_error(self, processor_name):
        return self.processors.get(processor_name=processor_name).error

    def save(self, *args, **kwargs):
        if self.pk:
            if self.processors.exists() and self.are_all_processors_complete:
                self.status = self.Status.COMPLETED
                self.end_time = timezone.now()
                if self.start_time:
                    self.run_duration = self.end_time - self.start_time
        super().save(*args, **kwargs)



class EventFlowProcessorState(TimeStampedModel):
    
    class Status(models.IntegerChoices):
        PENDING = 1
        IN_PROGRESS = 2
        COMPLETED = 3
        ERROR = 4
        COMPLETED_WITH_ERROR = 5
        ABORTED = 6
        RETRIABLE_ERROR = 7

    COMPLETION_STATES = (Status.COMPLETED, Status.COMPLETED_WITH_ERROR)
    
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True,
                          help_text=_("Unique ID"))
    
    event_flow = models.ForeignKey(EventFlow, related_name='processors', 
                                   on_delete=models.CASCADE)

    processor_name = models.CharField(max_length=32, help_text=_("Processor name"))

    result = models.JSONField(null=True, blank=True,
                               help_text=_("All the result of the task."))

    error = models.JSONField(null=True, blank=True,
                               help_text=_("Error stack trace of the task"))

    retriable_error = models.JSONField(null=True, blank=True,
                             help_text=_("Error stack trace of the task, only in case of a retriable error. Last error occurred will be stored."))
    
    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    
    run_duration = models.DurationField('Run duration', null=True, blank=True)

    start_time = models.DateTimeField('Start time of event flow', null=True, blank=True)

    end_time = models.DateTimeField('Start time of event flow', null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event_flow', 'processor_name'], name='unique_run')
        ]

class Question(models.Model):
    """
    Sanchit:TODO - Change DSA_PRACTICE type and CODING To category.
    Discuss with Product and maybe remove Coding or maybe add some field like 'proctored - bool'
    """
    class AnswerType(models.TextChoices):
        """
        Answer type signifies how the
        1. UI/UX should be for this question
        2. How evaluation should happen at a basic level.
        (Some details like prompt for evaluation might change based on other details of the question,
        but flow of evaluation will remain consistent for a particular answer type)
        3. Schema of question data.

        ANY OF THE ABOVE SHOULD ONLY BE DEPENDENT ON ANSWER TYPE AND AND NOT ON CATEGORY AND SUBCATEGORY.
        CATEGORY AND SUBCATEGORY ARE FOR THINGS LIKE FILTERING, ASSESSMENT CREATION ETC.
        """
        MCQ = 0, "MCQ",
        MMCQ = 1, "MMCQ",
        SUBJECTIVE = 2, "Subjective"
        VOICE = 3, "Voice"
    class Category(models.TextChoices):
        LOGICAL = 0, "Aptitude Test [Accenture]"
        LANGUAGE = 1, "Communication Skills"
        PERSONALITY = 2, "Psychometric Assessment"
        CODING = 3, "Coding Assessment"
        DSA_PRACTICE = 4, "DSA Practice"
        MOCK_BEHAVIOURAL = 5, "Mock Behavioural"
    class SubCategory(models.TextChoices):
        RC = 0, "Reading Comprehension"
        WRITING = 1, "Writing"
        SPEAKING = 2, "Speaking"
        LISTENING = 3, "Listening"
        NUMERICAL = 4, "Numerical"
        VERBAL = 5, "Verbal"
        NON_VERBAL = 6, "Non Verbal"
        DATA_INTERPRETATION = 7, "Data Interpretation"
        QUANT = 8, "Quantitative"
        DSA_PRACTICE_EASY = 9, "Easy"
        DSA_PRACTICE_MEDIUM = 10, "Medium"
        DSA_PRACTICE_HARD = 11, "Hard"
        DSA_PRACTICE_BASOC = 12,"Basic"

    id = models.AutoField(primary_key=True)
    answer_type = models.IntegerField(choices=AnswerType.choices, blank=True, null=True)
    question_data = models.JSONField(default=dict)
    '''
    Schema for question_data
    {
        "tags": [],
        "question": "",
        "companies": [],
        "resources": {},
        "titleSlug": "",
        "difficulty": "",
        "driver_codes": {
            "cpp": {
            "main_code": "",
            "user_code": ""
            },
            "java": {
            "main_code": "",
            "user_code": ""
            },
            "python": {
            "main_code": "",
            "user_code": ""
            },
            "javascript": {
            "main_code": "",
            "user_code": ""
            }
        },
        "questionTitle": "",
        "exampleTestcases": [],
        "additionalTestcases": []
    }'''
    markdown_question = models.TextField(blank=True, null=True)
    level = models.IntegerField(default=1, blank=True, null=True)
    audio_url = models.URLField(max_length=500, blank=True, null=True)
    tags = models.JSONField(default=list) #can be attention, processing-speed etc
    category = models.IntegerField(choices=Category.choices, blank=True, null=True) # can be logical, personality, etc
    sub_category = models.IntegerField(choices=SubCategory.choices, blank=True, null=True) # can be RC, Speaking, Reading, Writing
    time_required = models.DurationField(default=datetime.timedelta(minutes=1))
    source = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    @property
    def check_is_scoring_enabled(self):
        if self.category != int(Question.Category.PERSONALITY):
            return True
        return False
    
class UserEvalQuestionAttempt(models.Model):
    class Status(models.IntegerChoices):
        NOT_ATTEMPTED = 0, "Not Attempted"
        ATTEMPTED = 1, "Attempted"
        EVALUATING = 2, "Evaluating"
        EVALUATED = 3, "Evaluated"
        
    id = models.AutoField(primary_key=True)   
    user_id = models.ForeignKey(User, on_delete=models.DO_NOTHING, to_field='id')
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    assessment_attempt_id = models.ForeignKey('AssessmentAttempt', on_delete=models.DO_NOTHING, to_field='assessment_id', default=None)
    #Sanchit-TODO: How is section here being used and can it be Null then??
    section = models.CharField(max_length=255, blank=True, null=True) # can be RC, Speaking, Reading, Writing
    mcq_answer = models.IntegerField(blank=True, null=True)
    multiple_mcq_answer = ArrayField(models.IntegerField(), blank=True, null=True)
    answer_text = models.TextField(blank=True, null=True)    
    answer_audio_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.IntegerField(choices=Status.choices, default=Status.NOT_ATTEMPTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    eval_data = models.JSONField(default=dict, null=True)
    # eventflow_id = models.UUIDField(null=True) #Will store eventflow id if evaluation was done via eventflow
    evaluation_id = models.UUIDField(editable=False,default=uuid.uuid4)
    code = models.TextField(blank=True, null=True) 
    code_stubs=models.JSONField(blank=True, null=True)
    '''Schema for code_Stubs
            {
    "cpp": "",
    "java": "",
    "python": "",
    "javascript": ""
    }
    '''

    @property
    def converted_audio_path(self):
        # url_dir = os.path.dirname(self.answer_audio_url)
        # converted_audio_path = os.path.join(url_dir, "converted_audio.wav")
        converted_audio_path = f"{self.user_id}/{self.id}/converted_audio.wav"
        return converted_audio_path
    
    @property
    def audio_path(self):
        path = f"{self.user_id}/{self.id}/audio.wav"
        return path

    class Meta:
        unique_together = ('user_id', 'question','assessment_attempt_id')
	    
class AssessmentAttempt(models.Model):
    class Status(models.TextChoices):
        CREATION_PENDING = 0, "Not Started"
        IN_PROGRESS = 1, "In Progress"
        COMPLETED = 2, "Completed"
        EVALUATION_PENDING = 3, "Evaluation Pending"
        ABANDONED = 4, "Abandoned"
                
    class Type(models.TextChoices):
        LOGIC = 0, "Aptitude Test [Accenture]"
        LANGUAGE = 1, "Communication Skills"
        PERSONALITY = 2, "Psychometric Assessment"
        CODING = 3, "Coding Assessment"
        DSA_PRACTICE = 4, "DSA Practice"
        MOCK_BEHAVIOURAL = 5, "Mock Behavioural"
        LSRW=6, "LSRW"

    class Mode(models.TextChoices):
        EVALUATION = 0, "Evaluation"
        PRACTICE = 1, "Practice"

    assessment_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, to_field='id')
    assessment_generation_config_id = models.ForeignKey('AssessmentGenerationConfig', on_delete=models.DO_NOTHING, to_field='assessment_generation_id')
    attempted_list = models.JSONField(default=list) # stores list of UserEvalQuestionAttempt
    question_list = models.JSONField(default=list) # stores list of all questions
    type = models.IntegerField(choices=Type.choices, blank=True, null=True) # can be MVP1_Logic, MVP1_Language or MVP1_Personality
    last_saved = models.CharField(max_length=255, blank=True, null=True)
    last_saved_section = models.IntegerField(choices=Question.SubCategory.choices, blank=True, null=True)
    status = models.IntegerField(choices=Status.choices, default=Status.CREATION_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    evaluation_triggered = models.BooleanField(default=False)
    start_time = models.DateTimeField(blank=True, null=True)
    test_duration = models.DurationField()
    closed = models.BooleanField(default=False)  # set to True when the assessment is closed by the user (either in between or at the end)
    eval_data = models.JSONField(default=dict, null=True)
    assessment_url = models.TextField(blank=True, null=True)
    report_id = models.CharField(max_length=255, blank=True, null=True)
    mode = models.IntegerField(choices=Mode.choices, default=Mode.EVALUATION)
    
class AssessmentGenerationConfig(models.Model):
    class Type(models.TextChoices):
        Qualitative = 0, "Qualitative"
        Quantitative = 1, "Quantitative"
        
    enabled = models.BooleanField(default=True)
    assessment_generation_id = models.AutoField(primary_key=True)
    kwargs = models.JSONField(default=dict)
    assessment_generation_class_name  = models.CharField(max_length=255)
    evaluator_class_name = models.CharField(max_length=255)
    assessment_name = models.CharField(max_length=255, unique=True)
    assessment_display_name = models.CharField(max_length=255)
    number_of_attempts = models.IntegerField(default=2)
    assessment_type = models.IntegerField(choices=Type.choices, default=Type.Qualitative)
    test_duration = models.DurationField()
    display_data = models.JSONField(default=dict)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date=models.DateTimeField(blank=True,null=True)
    due_date=models.DateTimeField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    

class DSAPracticeChatData(models.Model):
    user_id = models.CharField(max_length=100)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    assessment_attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, to_field='assessment_id')
    chat_history = models.JSONField(default=list)
    chat_history_obj = models.ForeignKey(ChatHistory, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    chat_count = models.IntegerField(default=0)
    # [{"timestamp":<int>, "duration":<float|seconds>}]
    compile_duration_logs = models.JSONField(default=list,null=True,blank=True,help_text="Additional logs for monitoring purpose")
    # {"timestamp":<int>, "duration:<float|seconds>}
    submit_compile_log = models.JSONField(default=dict,null=True, blank=True,help_text="Log of submission compilation")

    class Meta:
        unique_together = ('user_id', 'question', 'assessment_attempt')

class QuestionIssues(models.Model):
    class TypeOfIssue(models.TextChoices):
        SOFTWARE_RELEATED_ISSUE = 0, "Software Releated Issue"
        CONTENT_RELEATED_ISSUE = 1, "Content Releated Issue"
        OTHERS_ISSUE = 2, "Others Issue"
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, to_field='id')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    assessment_attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, to_field='assessment_id')
    type_of_issue = models.IntegerField(choices=TypeOfIssue.choices)
    description = models.TextField(blank=False, null=False)

class DSASheetsConfig(models.Model):
    name=models.CharField(blank=False, null=False,unique=True,max_length=255)
    question_ids = models.JSONField(default=list)

