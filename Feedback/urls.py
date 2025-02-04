from django.urls import path

from Feedback.views import FeedbackFormView, UserFeedbackStatusView

urlpatterns = [
    path(
        "form",
        FeedbackFormView.as_view(),
        name="form",
    ),
    path(
        'status', 
        UserFeedbackStatusView.as_view(), 
        name='feedback-status'
    ),
]
