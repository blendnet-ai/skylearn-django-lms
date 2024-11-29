from accounts.models import (
    ConfigMap,
    Student,
    Lecturer,
    User,
    CourseProvider,
    CourseProviderAdmin,
)


class StudentRepository:
    def get_student_by_student_id(student_id):
        return Student.objects.get(student_id=student_id)

    def add_batch_by_student_id(student_id, batch):
        student = StudentRepository.get_student_by_student_id(student_id)
        student.batches.add(batch)
        student.save()

    def get_batches_by_student_id(student_id):
        return Student.objects.get(student_id=student_id).batches.all()

    def create_student(user):
        return Student.objects.create(student=user)


class UserRepository:
    @staticmethod
    def get_user_by_id(user_id):
        return User.objects.get(id=user_id)


class CourseProviderAdminRepository:
    @staticmethod
    def create_course_provider_admin(user):
        return CourseProviderAdmin.objects.create(course_provider_admin=user)


class CourseProviderRepository:
    @staticmethod
    def get_course_provider_by_user_id(user_id):
        try:
            # Fetch the CourseProviderAdmin instance using the user_id
            course_provider_admin = CourseProviderAdmin.objects.get(
                course_provider_admin__id=user_id
            )

            # Fetch the related CourseProvider instance
            course_provider = CourseProvider.objects.filter(
                admins=course_provider_admin
            ).first()

            if course_provider is None:
                return None

            return course_provider

        except CourseProviderAdmin.DoesNotExist:
            return None


class LecturerRepository:
    @staticmethod
    def get_presenter_details_by_lecturer_id(lecturer_id):
        try:
            lecturer = Lecturer.objects.get(lecturer_id=lecturer_id)
            return lecturer.presenter_details()
        except Lecturer.DoesNotExist:
            return None

    @staticmethod
    def create_lecturer(user, guid, upn):
        return Lecturer.objects.create(lecturer=user, guid=guid, upn=upn)


class ConfigMapRepository:
    @staticmethod
    def get_config_map(tag):
        try:
            return ConfigMap.objects.get(tag=tag)
        except ConfigMap.DoesNotExist:
            return None
