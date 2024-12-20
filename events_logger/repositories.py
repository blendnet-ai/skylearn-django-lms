from .models import PageEvent
from django.utils import timezone
from datetime import timedelta
from datetime import time, datetime, timedelta
from django.db import models
from django.db.models import Sum, DurationField, ExpressionWrapper, F
from datetime import timedelta


class PageEventRepository:
    @staticmethod
    def get_or_create_page_event(user, date, watched, time_spent, upload=None, upload_video=None, recording=None):
        page_event, created = PageEvent.objects.get_or_create(
            user=user,
            date=date,
            pdf=upload,
            video=upload_video,
            recording=recording,
            defaults={
                'watched': watched,
                'time_spent': time_spent
            }
        )
        return page_event, created
    @staticmethod
    def add_time_to_user_time(page_event, time_to_add):        
        page_event.time_spent += time_to_add
        page_event.watched = True
        page_event.save()
        
        return page_event
    
    @staticmethod
    def get_total_time_spent_by_user_on_resources_in_course(user, course):
        """
        Get total time spent by a user on all resources (uploads and videos) in a course
        
        Args:
            user: User object
            course: Course object
        
        Returns:
            timedelta: Total time spent by user in the course
        """
        # Get all page events for the user where either upload or upload_video belongs to the course
        page_events = PageEvent.objects.filter(
            user=user,
            watched=True
        ).filter(
            # Filter for either uploads or upload_videos that belong to the course
            models.Q(pdf__course=course) | 
            models.Q(video__course=course)|
            models.Q(recording__series__course_enrollments__batch__course=course)
        )

        # Sum the time_spent field
        total_time_spent = page_events.aggregate(
            total_time=Sum(ExpressionWrapper(F('time_spent'), output_field=DurationField()))
        )['total_time']
        
        # Ensure total_time_spent is not None
        if total_time_spent is None:
            total_time_spent = timedelta(0)
        
        return total_time_spent
    

    @staticmethod
    def get_total_videos_watched_by_user_in_course(user, course):
        """
        Get total number of videos watched by a user in a course
        
        Args:
            user: User object
            course: Course object
        
        Returns:
            int: Total number of videos watched by user in the course
        """
        # Get all page events for the user where upload_video belongs to the course
        total_videos_watched = PageEvent.objects.filter(
            user=user,
            watched=True,
            video__course=course
        ).distinct().count()

        return total_videos_watched
    
    
    @staticmethod
    def get_daily_resources_consumption_by_date_course_user(user_id, course_id, date):
        """
        Get daily resources entries for a specific date, course, and user.
        
        Args:
            user: User object
            course_id: ID of the course
            date: Date for which to retrieve resources (datetime.date)
        
        Returns:
            QuerySet: PageEvent objects for the specified date, course, and user
        """
        # Filter page events by user, course, and date
        daily_resources = PageEvent.objects.filter(
            user_id=user_id,
            date=date
        ).filter(
            # Filter for either uploads or upload_videos that belong to the course
            models.Q(pdf__course__id=course_id) | 
            models.Q(video__course__id=course_id)|
            models.Q(recording__series__course_enrollments__batch__course_id=course_id)
        )
        
        return daily_resources