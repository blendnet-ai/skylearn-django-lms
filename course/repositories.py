from course.models import Batch, Course, LiveClassSeriesBatchAllocation, CourseAllocation


class CourseRepository:
    @staticmethod
    def get_course_by_id(course_id):
        return Course.objects.get(id=course_id)
    
    def get_courses_by_course_provider(course_provider_id):
        return Course.objects.filter(course_provider_id=course_provider_id)
    
    


class BatchRepository:
    @staticmethod
    def create_batch(course, title, lecturer):
        return Batch.objects.create(course=course, title=title, lecturer=lecturer)

    @staticmethod
    def get_batch_by_id(batch_id):
        return Batch.objects.get(id=batch_id)

    @staticmethod
    def get_batches_by_course_id(course_id):
        return Batch.objects.filter(course_id=course_id)

    @staticmethod
    def get_batches_by_lecturer_id(lecturer_id):
        return Batch.objects.filter(lecturer_id=lecturer_id)


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