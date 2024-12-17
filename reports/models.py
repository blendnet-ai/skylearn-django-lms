from django.db import models
from django.conf import settings
from datetime import timedelta
from course.models import Course

class UserCourseReport(models.Model):
    """
    Stores aggregated time spent data for a user in a course across different activities
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE)
    
    # Time spent on assessments
    assessment_time = models.DurationField(default=timedelta())
    
    # Time spent on resources (reading materials, videos etc)
    resource_time_video = models.DurationField(default=timedelta())
    resource_time_reading=models.DurationField(default=timedelta())
    time_spent_in_live_classes=models.DurationField(default=timedelta())
    # Classes attended data
    total_classes = models.IntegerField(default=0)
    classes_attended = models.IntegerField(default=0)
    
    # Total time calculations
    total_time_spent = models.DurationField(default=timedelta())
    
    # Tracking fields
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['last_updated'])
        ]
        
        
class DailyAggregation(models.Model):
    """
    Stores daily aggregation of time spent by a user on different types of fields
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    type_of_aggregation = models.CharField(max_length=100)  # Adjust max_length as needed
    time_spent = models.DurationField(default=timedelta())
    reference_id = models.IntegerField(null=True)

    class Meta:
        unique_together = ('user', 'date', 'type_of_aggregation', 'course')
        indexes = [
            models.Index(fields=['user_id', 'date']),
            models.Index(fields=['type_of_aggregation'])
        ]
        
        