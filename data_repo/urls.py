from django.urls import path

from .views import ProfilePageContent, ConfigMapAPIView, InstituteNameAutoFill

urlpatterns = [
    path('profile_page_content', ProfilePageContent.as_view(), name='get_profile_page_content'),
    path('config_map/<slug:tag>', ConfigMapAPIView.as_view(), name='get_config_map'),
    path('institute_name_autofill', InstituteNameAutoFill.as_view(), name='get_institute_name_autofill'),
]
