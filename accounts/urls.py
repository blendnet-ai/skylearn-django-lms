from django.urls import path, include

from .views import (
    enroll_students_in_batch,
    get_course_provider,
    update_student_status,
    get_lecturers_by_provider
)



urlpatterns = [
    path(
        "enroll_students_in_batch/",
        enroll_students_in_batch,
        name="enroll_students_in_batch",
    ),
    path("get-course-provider",get_course_provider,name="get_course_provider"),
    path(
        'student/<int:student_id>/status/',
        update_student_status,
        name='update_student_status'
    ),
    path(
        'course-provider/<int:course_provider_id>/lecturers/',
        get_lecturers_by_provider,
        name='get_lecturers_by_provider'
    )

]
