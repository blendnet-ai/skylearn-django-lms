from accounts.models import Student, User


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
