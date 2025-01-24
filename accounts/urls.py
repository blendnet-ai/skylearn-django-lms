from django.urls import path, include

from .views import (
    enroll_students_in_batch,
    get_course_provider
)



urlpatterns = [
    path(
        "enroll_students_in_batch/",
        enroll_students_in_batch,
        name="enroll_students_in_batch",
    ),
    path("get-course-provider",get_course_provider,name="get_course_provider")
]
