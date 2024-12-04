from django.urls import path
from . import views

urlpatterns = [
    # Program urls
    path("", views.ProgramFilterView.as_view(), name="programs"),
    path("<int:pk>/detail/", views.program_detail, name="program_detail"),
    path("add/", views.program_add, name="add_program"),
    path("<int:pk>/edit/", views.program_edit, name="edit_program"),
    path("<int:pk>/delete/", views.program_delete, name="program_delete"),
    # Course urls
    path("course/<slug>/detail/", views.course_single, name="course_detail"),
    path("<int:pk>/course/add/", views.course_add, name="course_add"),
    path("course/<slug>/edit/", views.course_edit, name="edit_course"),
    path("course/delete/<slug>/", views.course_delete, name="delete_course"),
    # CourseAllocation urls
    path(
        "course/assign/",
        views.CourseAllocationFormView.as_view(),
        name="course_allocation",
    ),
    path(
        "course/allocated/",
        views.CourseAllocationFilterView.as_view(),
        name="course_allocation_view",
    ),
    path(
        "allocated_course/<int:pk>/edit/",
        views.edit_allocated_course,
        name="edit_allocated_course",
    ),
    path(
        "course/<int:pk>/deallocate/", views.deallocate_course, name="course_deallocate"
    ),
    # # File uploads urls
    # path(
    #     "course/<slug>/documentations/upload/",
    #     views.handle_file_upload,
    #     name="upload_file_view",
    # ),
    # path(
    #     "course/<slug>/documentations/<int:file_id>/edit/",
    #     views.handle_file_edit,
    #     name="upload_file_edit",
    # ),
    path(
        "course/<slug>/documentations/<int:file_id>/delete/",
        views.handle_file_delete,
        name="upload_file_delete",
    ),
    # Video uploads urls
    # path(
    #     "course/<slug>/video_tutorials/upload/",
    #     views.handle_video_upload,
    #     name="upload_video",
    # ),
    path(
        "course/<slug>/video_tutorials/<video_slug>/detail/",
        views.handle_video_single,
        name="video_single",
    ),
    # path(
    #     "course/<slug>/video_tutorials/<video_slug>/edit/",
    #     views.handle_video_edit,
    #     name="upload_video_edit",
    # ),
    path(
        "course/<slug>/video_tutorials/<video_slug>/delete/",
        views.handle_video_delete,
        name="upload_video_delete",
    ),
    # course registration
    path("course/registration/", views.course_registration, name="course_registration"),
    path("course/drop/", views.course_drop, name="course_drop"),
    path("my_courses/", views.user_course_list, name="user_course_list"),
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
    path("course/<course_id>/get-batches/", views.get_batches_by_course_id, name="get_batches"),
    path("course-provider/<course_provider_id>/get-courses/", views.get_courses_by_course_provider_id, name="get_batches"),
    path("course/<course_id>/batch/<batch_id>/get-modules-data/", views.get_modules_and_resources_by_course_id_and_batch_id, name="get_modules_data"),
    path("course/resource/get-sas-url/", views.get_sas_url_for_recording, name="get_sas_url_for_recording"),
    path("course/user-courses-list",views.user_courses_list,name="user_courses_list"),
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
]
