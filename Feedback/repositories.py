from Feedback.models import FeedbackForm, FeedbackResponse
from datetime import datetime,timedelta
from django.utils import timezone
from Feedback.models import CourseFormEntry

class FeedbackFormRepository:
    @staticmethod
    def get_by_name(name):
        try:
            feedback_form = FeedbackForm.objects.get(name=name)
            return feedback_form
        except FeedbackForm.DoesNotExist:
            return None

    @staticmethod
    def get(id):
        try:
            feedback_form = FeedbackForm.objects.get(id=id)
            return feedback_form
        except FeedbackForm.DoesNotExist:
            return None

    @staticmethod
    def get_forms_by_user_and_batch(user_id, batch_id, current_date):
        """
        Get all feedback forms for a specific batch
        Returns all forms with their status indicating whether they are:
        1. Filled (has response from user)
        2. Currently active (current_date between start_date and end_date)
        3. Overdue (end_date < current_date and no response)

        """
        
        # Get all form entries for this batch
        form_entries = CourseFormEntry.objects.filter(
            batch_id=batch_id
        ).select_related('form').order_by('id')
        
        # Get all responses for this user
        filled_forms_ids = FeedbackResponse.objects.filter(
            user_id=user_id,
            course_feedback_entry__batch_id=batch_id
        ).values_list('course_feedback_entry_id', flat=True)
        
        filled_forms = FeedbackResponse.objects.filter(
            user_id=user_id,
            course_feedback_entry__batch_id=batch_id
        )
        
        # Format the response
        forms = [{
            'form_name': entry.form.name,
            "form_id":entry.form_id,
            'entry_form_id': entry.id,
            'start_date': entry.start_date,
            'end_date': entry.end_date,
            'is_overdue': entry.end_date <= current_date and entry.id not in filled_forms_ids,
            'is_filled': entry.id in filled_forms_ids,
            'filled_on': filled_forms.filter(course_feedback_entry_id=entry.id).first().created_at if filled_forms.filter(course_feedback_entry_id=entry.id).exists() else None,
            'is_unlocked': entry.start_date <= current_date,
            'week_label': f'Week {index + 1}'
        } for index, entry in enumerate(form_entries)]
        
        return forms
    
    @staticmethod
    def check_if_any_pending_mandatory_forms(user_id, batch_id, current_date):
        """
        Check if there are any pending mandatory forms for a user in a specific batch
        """
        # Get all form entries for this batch
        form_entries = CourseFormEntry.objects.filter(
            batch_id=batch_id,
            form__is_mandatory=True,
            end_date__lte=current_date
        ).select_related('form')
        
        # Get all responses for this user
        filled_forms = FeedbackResponse.objects.filter(
            user_id=user_id,
            course_feedback_entry__batch_id=batch_id
        ).values_list('course_feedback_entry_id', flat=True)
        
        # Check if any mandatory forms are pending
        return any(entry.id not in filled_forms for entry in form_entries)
    
    @staticmethod
    def get_pending_mandatory_forms_bulk(student_ids, batch_ids, cutoff_date):
        """Get all pending mandatory feedback forms and filled responses for multiple students and batches
        
        Args:
            student_ids (list): List of student IDs
            batch_ids (list): List of batch IDs
            cutoff_date (date): Date before which forms should have been filled
            
        Returns:
            tuple: (mandatory_forms QuerySet, filled_forms QuerySet)
        """
        form_entries = CourseFormEntry.objects.filter(
            batch_id__in=batch_ids,
            form__is_mandatory=True,
            end_date__lte=cutoff_date,
        ).select_related('form', 'batch')

        filled_forms = FeedbackResponse.objects.filter(
            user_id__in=student_ids,
            course_feedback_entry__batch_id__in=batch_ids
        ).values_list('user_id', 'course_feedback_entry_id')

        return form_entries, filled_forms


class FeedbackResponseRepository:
    @staticmethod
    def get_feedback_responses_by_user_ids(user_ids):
        feedback_responses = FeedbackResponse.objects.filter(user_id__in=user_ids)
        return feedback_responses

    @staticmethod
    def is_feedback_filled_for_week(user_id, week_start_date):
        """
        Check if user has filled feedback for the current week since batch start
        """
        return FeedbackResponse.objects.filter(
            user_id=user_id,
            created_at__gte=week_start_date,
            created_at__lt=week_start_date + timedelta(days=7)
        ).exists()
    
    @staticmethod
    def create(**data):
        return FeedbackResponse.objects.create(**data)


class CourseFormEntryRepository:
    @staticmethod
    def get(id):
        return CourseFormEntry.objects.get(id=id)