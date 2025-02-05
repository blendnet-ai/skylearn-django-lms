from course.models import (
    Batch,
    Course,
    LiveClassSeriesBatchAllocation,
    CourseAllocation,
    Module,
    Upload,
    UploadVideo
)
from evaluation.models import AssessmentGenerationConfig
from django.db.models import Prefetch, F, CharField, Value
from django.db.models.functions import Concat


class CourseRepository:
    @staticmethod
    def get_course_by_id(course_id):
        return Course.objects.get(id=course_id)

    @staticmethod
    def get_courses_by_course_provider(course_provider_id):
        return Course.objects.filter(course_provider_id=course_provider_id)

    @staticmethod
    def get_courses_for_lecturer(user_id):
        return Course.objects.filter(allocated_course__lecturer__pk=user_id).values()

    @staticmethod
    def get_courses_for_student(user_id):
        return (
        Course.objects.filter(batch__student__student_id=user_id)
        .prefetch_related(
            Prefetch(
                "allocated_course",
                queryset=CourseAllocation.objects.select_related("lecturer"),
            )
        )
        .annotate(
            lecturer_full_name=Concat(
                F("batch__lecturer__first_name"),  # Use batch's lecturer
                Value(" "),
                F("batch__lecturer__last_name"),
                output_field=CharField(),
            ),
            batch_id=F("batch__id")
        )
        .values()
    )

    @staticmethod
    def get_all_courses():
        return Course.objects.all().values()
    
    @staticmethod
    def get_courses_for_course_provider_admin(course_provider_admin_id):
        return Course.objects.filter(
            course_provider__admins__course_provider_admin_id=course_provider_admin_id
        ).values()

    @staticmethod
    def get_course_by_code(course_code):
        return Course.objects.filter(code=course_code).first()

    @staticmethod
    def get_assessment_count_by_course_id(course_id):
        return AssessmentGenerationConfig.objects.filter(
            modules__course_id=course_id
        ).count()

class BatchRepository:
    @staticmethod
    def create_batch(course, title, lecturer, start_date=None, end_date=None):
        return Batch.objects.get_or_create(course=course, title=title, lecturer=lecturer, start_date=start_date, end_date=end_date)

    @staticmethod
    def get_batch_by_id(batch_id):
        return Batch.objects.get(id=batch_id)

    @staticmethod
    def get_batches_by_course_id(course_id):
        return Batch.objects.filter(course_id=course_id)

    @staticmethod
    def get_batches_by_lecturer_id(lecturer_id):
        return Batch.objects.filter(lecturer_id=lecturer_id)

    @staticmethod
    def set_batch_lecturer(batch_id, lecturer):
        batch = Batch.objects.get(id=batch_id)
        batch.lecturer = lecturer
        batch.save()
        return batch
    
    @staticmethod
    def get_all_batches():
        return Batch.objects.all()
    
    @staticmethod
    def get_batch_by_user_id_and_course_id(user_id, course_id):
        return Batch.objects.filter(student__student_id=user_id, course_id=course_id).first()




class LiveClassSeriesBatchAllocationRepository:
    @staticmethod
    def get_live_classe_series_by_batch_id(batch_id):
        return LiveClassSeriesBatchAllocation.objects.filter(
            batch_id=batch_id
        ).values_list("live_class_series_id", flat=True)

    @staticmethod
    def create_live_class_series_batch_allocation(meeting_series, batch):
        allocation = LiveClassSeriesBatchAllocation.objects.create(
            live_class_series=meeting_series, batch=batch
        )
        return allocation

    @staticmethod
    def get_batch_ids_by_live_class_series_id(live_class_series_id):
        return LiveClassSeriesBatchAllocation.objects.filter(
            live_class_series_id=live_class_series_id
        ).values_list("batch_id", flat=True)

    @staticmethod
    def delete_live_class_series_batch_allocation(live_class_series, batch_id):
        LiveClassSeriesBatchAllocation.objects.filter(
            live_class_series=live_class_series, batch_id=batch_id
        ).delete()


class ModuleRepository:
    @staticmethod
    def get_or_create_module(course, title, order_in_course):
        return Module.objects.get_or_create(
            course=course,
            title=title,
            order_in_course=order_in_course
        )
        
    @staticmethod
    def get_module_details_by_course_id(course_id):
        modules = (
            Module.objects.filter(course_id=course_id)
            .prefetch_related(
                Prefetch("uploads", queryset=Upload.objects.all()),
                Prefetch("video_uploads", queryset=UploadVideo.objects.all()),
                Prefetch(
                    "assignment_configs",
                    queryset=AssessmentGenerationConfig.objects.all(),
                ),
            )
            .order_by("order_in_course")
        )
        return modules


class UploadRepository:
    @staticmethod
    def get_existing_upload(file_name, course, module):
        return Upload.objects.filter(
            title=file_name,
            course=course,
            module=module
        ).first()

    @staticmethod
    def create_upload(title, course, module, blob_url):
        return Upload.objects.create(
            title=title,
            course=course,
            module=module,
            blob_url=blob_url
        )
    
    def get_reading_resource_by_id(resource_id):
        resource=Upload.objects.filter(id=resource_id).first()
        return resource

class UploadVideoRepository:
    @staticmethod
    def get_existing_upload(file_name, course, module):
        return UploadVideo.objects.filter(
            title=file_name,
            course=course,
            module=module
        ).first()

    @staticmethod
    def create_upload(title, course, module, blob_url):
        return UploadVideo.objects.create(
            title=title,
            course=course,
            module=module,
            blob_url=blob_url
        )

    @staticmethod
    def get_video_count_by_course(course_id):
        videos = UploadVideo.objects.filter(course_id=course_id)
        return videos.count()
    
    def get_video_resource_by_id(resource_id):
        resource=UploadVideo.objects.filter(id=resource_id).first()
        return resource
        


