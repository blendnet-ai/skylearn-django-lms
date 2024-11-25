from django.conf import settings

class FeedbackFormProvider:
    @staticmethod
    def get_feedback_form_url():
        """Returns the feedback form URL"""
        URL = settings.FEEDBACK_FORM_URL
        return URL
