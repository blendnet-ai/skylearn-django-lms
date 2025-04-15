from course.models import (
    Batch,
    Course,
    LiveClassSeriesBatchAllocation,
    CourseAllocation,
    Module,
    Upload,
    UploadVideo,
)
from evaluation.models import AssessmentGenerationConfig
from django.db.models import Prefetch, F, CharField
from django.db import connection
from django.db.models.functions import Concat
from django.db import transaction, IntegrityError


class CourseRepository:
    @staticmethod
    def create_course(course_provider, code, title, summary, course_hours):
        return Course.objects.create(
            title=title,
            summary=summary,
            code=code,
            course_hours=course_hours,
            course_provider=course_provider,
        )

    @staticmethod
    def get_course_by_id(course_id):
        try:
            return Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return None

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
                batch_id=F("batch__id"),
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
    def create_batch(
        course, title, lecturer, start_date=None, end_date=None, form=None
    ):
        return Batch.objects.get_or_create(
            course=course,
            title=title,
            lecturer=lecturer,
            start_date=start_date,
            end_date=end_date,
            form=form,
        )

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
        return Batch.objects.filter(
            student__student_id=user_id, course_id=course_id
        ).first()


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
    def get_module_by_id(module_id):
        try:
            return Module.objects.get(id=module_id)
        except Module.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_module(course, title, order_in_course):
        return Module.objects.get_or_create(
            course=course, title=title, order_in_course=order_in_course
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

    @staticmethod
    def shift_module_orders(
        course_id: int, from_order: int, shift_up: bool = True
    ) -> None:
        """
        Shifts module orders up or down
        Args:
            course_id: ID of the course
            from_order: Starting order number to shift from
            shift_up: If True, shifts orders up (+1), if False shifts down (-1)
        """
        with transaction.atomic():
            modules = Module.objects.filter(
                course_id=course_id, order_in_course__gte=from_order
            )

            if shift_up:
                # Move modules up one position, starting from the highest order
                for module in modules.order_by("-order_in_course"):
                    module.order_in_course += 1
                    module.save()
            else:
                # Move modules down one position, starting from the lowest order
                for module in modules.order_by("order_in_course"):
                    module.order_in_course -= 1
                    module.save()

    @staticmethod
    def create_module(course, title, order_in_course):
        """Create a new module with proper order handling"""
        with transaction.atomic():
            # Get max order in the course
            max_order = (
                Module.objects.filter(course_id=course.id)
                .order_by("-order_in_course")
                .first()
            )
            max_order = max_order.order_in_course if max_order else 0

            # Validate and adjust order if needed
            if order_in_course > max_order + 1:
                order_in_course = max_order + 1
            elif order_in_course < 1:
                order_in_course = 1

            # Shift modules in reverse order to prevent conflicts
            modules_to_shift = Module.objects.filter(
                course_id=course.id, order_in_course__gte=order_in_course
            ).order_by("-order_in_course")

            for module in modules_to_shift:
                module.order_in_course += 1
                module.save()

            # Create new module
            try:
                module = Module.objects.create(
                    course=course, title=title, order_in_course=order_in_course
                )
                return module
            except IntegrityError:
                # If there's still a conflict, append to the end
                latest_order = Module.objects.filter(course_id=course.id).count() + 1
                module = Module.objects.create(
                    course=course, title=title, order_in_course=latest_order
                )
                # Ensure proper ordering
                ModuleRepository.reorder_modules(course.id)
                return module

    @staticmethod
    def update_module(module_id, **kwargs):
        """Update module with completely separate order handling phases"""
        with transaction.atomic():
            # Get the module and its course
            module = Module.objects.select_for_update().get(id=module_id)
            course_id = module.course.id
            new_order = kwargs.pop("order_in_course", None)  # Remove order from kwargs

            # Update non-order fields first
            for key, value in kwargs.items():
                if value is not None:
                    setattr(module, key, value)

            # Save changes to other fields (if any)
            if kwargs:
                module.save()

            # Handle order change as a completely separate operation
            if new_order is not None and new_order != module.order_in_course:
                # Let's handle reordering outside the main flow
                ModuleRepository._reorder_all_modules(course_id, module_id, new_order)

            # Refresh to get latest state
            module.refresh_from_db()
            return module

    @staticmethod
    def _reorder_all_modules(course_id, target_module_id, new_order):
        """Complete rebuild of module ordering to avoid any conflicts"""
        with transaction.atomic():
            # Get all modules
            all_modules = list(
                Module.objects.select_for_update().filter(course_id=course_id)
            )

            # Validate new order
            if new_order < 1:
                new_order = 1
            elif new_order > len(all_modules):
                new_order = len(all_modules)

            # Find the target module and its current order
            target_module = next(
                (m for m in all_modules if m.id == target_module_id), None
            )
            if not target_module:
                return

            current_order = target_module.order_in_course

            # Skip if no change needed
            if new_order == current_order:
                return

            # First, assign temporary orders
            # Use module ID as temporary order to guarantee uniqueness
            for mod in all_modules:
                if (
                    mod.order_in_course != mod.id + 10000
                ):  # Use offset to avoid conflicts
                    mod.order_in_course = mod.id + 10000
                    mod.save(update_fields=["order_in_course"])

            # Create new ordering list (excluding target)
            other_modules = [m for m in all_modules if m.id != target_module_id]
            other_modules.sort(key=lambda m: m.id + 10000)  # Sort by temp order

            # Rebuild the order from scratch
            final_order = 1

            # Process modules before insertion point
            for i in range(new_order - 1):
                if i < len(other_modules):
                    other_modules[i].order_in_course = final_order
                    other_modules[i].save(update_fields=["order_in_course"])
                    final_order += 1

            # Insert target module
            target_module.order_in_course = final_order
            target_module.save(update_fields=["order_in_course"])
            final_order += 1

            # Process remaining modules
            for i in range(new_order - 1, len(other_modules)):
                other_modules[i].order_in_course = final_order
                other_modules[i].save(update_fields=["order_in_course"])
                final_order += 1


class UploadRepository:
    @staticmethod
    def get_existing_upload(file_name, course, module):
        return Upload.objects.filter(
            title=file_name, course=course, module=module
        ).first()

    @staticmethod
    def create_upload(title, course, module, blob_url):
        return Upload.objects.create(
            title=title, course=course, module=module, blob_url=blob_url
        )

    @staticmethod
    def get_reading_resource_by_id(resource_id):
        resource = Upload.objects.filter(id=resource_id).first()
        return resource


class UploadVideoRepository:
    @staticmethod
    def get_existing_upload(file_name, course, module):
        return UploadVideo.objects.filter(
            title=file_name, course=course, module=module
        ).first()

    @staticmethod
    def create_upload(title, course, module, blob_url):
        return UploadVideo.objects.create(
            title=title, course=course, module=module, blob_url=blob_url
        )

    @staticmethod
    def get_video_count_by_course(course_id):
        videos = UploadVideo.objects.filter(course_id=course_id)
        return videos.count()

    @staticmethod
    def get_video_resource_by_id(resource_id):
        resource = UploadVideo.objects.filter(id=resource_id).first()
        return resource
