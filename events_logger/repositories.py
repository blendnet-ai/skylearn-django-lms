from .models import PageEvent
from django.utils import timezone
from datetime import timedelta
from datetime import time, datetime, timedelta
from django.db import models

class PageEventRepository:
    @staticmethod
    def get_or_create_page_event(user, date, watched, time_spent, upload=None, upload_video=None):
        page_event, created = PageEvent.objects.get_or_create(
            user=user,
            date=date,
            pdf=upload,
            video=upload_video,
            defaults={
                'watched': watched,
                'time_spent': time_spent
            }
        )
        return page_event, created
    @staticmethod
    def add_time_to_user_time(page_event,time_to_add):
        # Convert time_to_add string to timedelta
        if isinstance(time_to_add, str):
            time_parts = list(map(int, time_to_add.split(':')))
            time_to_add = timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])
        
        # Add the new time
        total_seconds = page_event.time_spent.hour * 3600 + page_event.time_spent.minute * 60 + page_event.time_spent.second
        time_to_add_seconds = time_to_add.seconds
        
        new_total_seconds = total_seconds + time_to_add_seconds
        
        # Convert back to hours, minutes, seconds
        hours = new_total_seconds // 3600
        minutes = (new_total_seconds % 3600) // 60
        seconds = new_total_seconds % 60
        page_event.watched=True
        # Create a new time object
        page_event.time_spent = time(hour=hours, minute=minutes, second=seconds)
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
            models.Q(video__course=course)
        )

        total_seconds = 0
        for event in page_events:
            if event.time_spent:
                # Convert time_spent to total seconds directly
                total_seconds += event.time_spent.total_seconds()  # Updated line

        # Convert total seconds to timedelta
        return timedelta(seconds=total_seconds)
    

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
        ).count()

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
            models.Q(video__course__id=course_id)
        )
        
        return daily_resources