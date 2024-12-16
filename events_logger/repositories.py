from .models import PageEvent
from django.utils import timezone
from datetime import timedelta
from datetime import time, datetime, timedelta
from django.db import models

class PageEventRepository:
    @staticmethod
    def get_or_create_page_event(user, upload=None, upload_video=None):
        page_event, created = PageEvent.objects.get_or_create(
            user=user,
            upload=upload,
            upload_video=upload_video
        )
        return page_event, created
    
    @staticmethod
    def add_time_to_user_time(user, time_to_add, upload=None, upload_video=None):
        # Convert time_to_add string to timedelta
        if isinstance(time_to_add, str):
            time_parts = list(map(int, time_to_add.split(':')))
            time_to_add = timedelta(hours=time_parts[0], minutes=time_parts[1], seconds=time_parts[2])

        page_event, created = PageEvent.objects.get_or_create(
            user=user,
            upload=upload,
            upload_video=upload_video,
            defaults={'time_spent': time(0, 0, 0)}
        )
        
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
            models.Q(upload__course=course) | 
            models.Q(upload_video__course=course)
        )

        total_seconds = 0
        for event in page_events:
            if event.time_spent:
                # Convert time object to seconds
                total_seconds += (
                    event.time_spent.hour * 3600 + 
                    event.time_spent.minute * 60 + 
                    event.time_spent.second
                )

        # Convert total seconds to timedelta
        return timedelta(seconds=total_seconds)
    
    
    
        