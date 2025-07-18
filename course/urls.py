from django.urls import path
from . import views

urlpatterns = [
    path(
        "live_classes/series/create/",
        views.create_live_class_series,
        name="create_live_class_series",
    ),
    path(
        "live_classes/series/<int:id>/update/",
        views.update_live_class_series,
        name="update_live_class_series",
    ),
    path(
        "live_classes/series/<int:id>/delete/",
        views.delete_live_class_series,
        name="delete_live_class_series",
    ),
    path(
        "live_classes/class/batch/<int:batch_id>/",
        views.get_live_classes_by_batch_id,
        name="get_live_classes_by_batch_id",
    ),
    path(
        "live_classes/class/course/<int:course_id>/",
        views.get_live_classes_by_course_id,
        name="get_live_classes_by_course_id",
    ),
    path(
        "live_classes/class/",
        views.get_live_classes,
        name="get_live_classes_by_course_id",
    ),
    path(
        "live_classes/class/<int:id>/update/",
        views.update_live_class,
        name="update_live_class",
    ),
    path(
        "live_classes/class/<int:id>/delete/",
        views.delete_live_class,
        name="delete_live_class",
    ),
    path("course/<course_id>/batch/create/", views.create_batch, name="create_batch"),
    path(
        "course/<course_id>/get-batches/",
        views.get_batches_by_course_id,
        name="get_batches",
    ),
    path(
        "course-provider/<course_provider_id>/get-courses/",
        views.get_courses_by_course_provider_id,
        name="get_batches",
    ),
    path(
        "course/<course_id>/get-modules-data/",
        views.get_modules_and_resources_by_course_id,
        name="get_modules_data",
    ),
    path(
        "course/<course_id>/get-assessment-configs/<module_id>/",
        views.get_assessments_by_module_id,
        name="get_assessments",
    ),
    path("course/resource/get-sas-url/", views.get_sas_url, name="get_sas_url"),
    path("course/get-recordings/", views.get_recordings, name="get_recordings"),
    path("course/user-courses-list", views.user_courses_list, name="user_courses_list"),
    path(
        "live_classes/class/<int:meeting_id>/details",
        views.get_meeting_details,
        name="get_meeting_details",
    ),
    path(
        "live_classes/series/<int:series_id>/details",
        views.get_live_class_details,
        name="get_series_details",
    ),
    path("course/students-list/", views.get_students_list, name="get_students_list"),
    path(
        "course/student-details/<int:student_id>/",
        views.get_student_details,
        name="get_student_details",
    ),
    path(
        "course/send-batch-message",
        views.send_course_batch_message,
        name="get_student_details",
    ),
    path(
        "course/send-personal-message",
        views.send_course_personal_message,
        name="send_course_personal_message",
    ),
    path(
        "course/<course_id>/batch/create-with-students/",
        views.create_batch_with_students,
        name="create_batch_with_students",
    ),
    path(
        "course/<course_code>/get-unassigned-students/",
        views.get_unassigned_students,
        name="get_unassigned_students",
    ),
    path(
        "student-dashboard/",
        views.get_student_dashboard_data,
        name="get_student_dashboard_data",
    ),
    path("bulk-enroll/", views.BulkEnrollmentView.as_view(), name="bulk-enroll"),
    path("bulk-enroll-lecturer/", views.LecturerBulkEnrollmentView.as_view(), name="bulk-enroll-lecturer"),
    path(
        "course/<int:course_id>/student/<int:student_id>/unenroll/",
        views.remove_student_enrollment,
        name="remove_student_enrollment",
    ),
    path("course/create/", views.create_course, name="create_course"),
    path("course/<int:course_id>/update/", views.update_course, name="update_course"),
    path("course/<int:course_id>/delete/", views.delete_course, name="delete_course"),
    path(
        "course/<int:course_id>/module/create/",
        views.create_module,
        name="create_module",
    ),
    path(
        "course/<int:course_id>/module/<int:module_id>/update/",
        views.update_module,
        name="update_module",
    ),
    path(
        "course/<int:course_id>/module/<int:module_id>/delete/",
        views.delete_module,
        name="delete_module",
    ),
    path(
        "materials/upload/",
        views.upload_material,
        name="upload_material",
    ),
    path(
        "materials/<str:type>/<int:upload_id>/delete/",
        views.delete_material,
        name="delete_material",
    ),
    path(
        "get-course/<int:course_id>/",
        views.get_course_by_id,
        name="get_course_by_id",
    ),
    path(
        "get-module/<int:module_id>/",
        views.get_module_by_id,
        name="get_module_by_id",
    ),
    path("create-assessment/", views.create_assessment, name="create_assessment"),
    path(
        "modules/<int:module_id>/delete-assessment/<int:assessment_generation_id>/",
        views.delete_assessment,
        name="delete_assessment",
    ),
    path("questions/upload/", views.question_upload, name="upload-questions"),
    path(
        "assessment/<int:assessment_generation_id>/update/",
        views.update_assessment_config,
        name="update_assessment_config",
    ),
    path(
        "assessment/<int:assessment_generation_id>/details/",
        views.get_assessment_config_details,
        name="get_assessment_config_details",
    ),
    path("batch/<int:batch_id>/update/", views.update_batch, name="update_batch"),
    path("batch/<int:batch_id>/delete/", views.delete_batch, name="delete_batch"),
    path(
        "batch/<int:batch_id>/",
        views.get_batch_by_id_and_course,
        name="get-batch-details",
    ),
]
