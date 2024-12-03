from accounts.models import Student, Lecturer, User, CourseProvider,CourseProviderAdmin


class StudentRepository:
    def get_student_by_student_id(student_id):
        return Student.objects.get(student_id=student_id)

    def add_batch_by_student_id(student_id, batch):
        student = StudentRepository.get_student_by_student_id(student_id)
        student.batches.add(batch)
        student.save()

    def get_batches_by_student_id(student_id):
        return Student.objects.get(student_id=student_id).batches.all()


class UserRepository:
    def get_user_by_id(user_id):
        return User.objects.get(id=user_id)


class CourseProviderRepository:
    @staticmethod
    def get_course_provider_by_user_id(user_id):
        try:
            # Fetch the CourseProviderAdmin instance using the user_id
            course_provider_admin = CourseProviderAdmin.objects.get(course_provider_admin__id=user_id)
            
            # Fetch the related CourseProvider instance
            course_provider = CourseProvider.objects.filter(admins=course_provider_admin).first()
            
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
    def get_all_unique_presenter_guids():
        return Lecturer.objects.exclude(guid__isnull=True).values_list('guid', flat=True).distinct()
        