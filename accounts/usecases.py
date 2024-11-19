from accounts.models import Student
from accounts.repositories import StudentRepository
from course.repositories import BatchRepository


class BatchAllocationUsecase:
    @staticmethod
    def enroll_students_in_batch(batch_id, student_ids):
        batch = BatchRepository.get_batch_by_id(batch_id)

        enrolled_students = []
        failed_to_enroll_studends = []

        for student_id in student_ids:
            try:
                # One student can be enrolled in only one batch of a course
                if not BatchAllocationUsecase.does_batch_of_course_exist(
                    student_id, batch.course.id
                ):
                    StudentRepository.add_batch_by_student_id(student_id, batch)
                    enrolled_students.append(student_id)
                else:
                    failed_to_enroll_studends.append(
                        {
                            "student_id": student_id,
                            "reason": "Student is already enrolled in one of the batches of this course.",
                        }
                    )
            except Student.DoesNotExist:
                failed_to_enroll_studends.append(
                    {"student_id": student_id, "reason": "Student does not exists."}
                )
        return enrolled_students, failed_to_enroll_studends

    @staticmethod
    def does_batch_of_course_exist(student_id, course_id):
        student_batches = StudentRepository.get_batches_by_student_id(student_id)
        return any(batch.course.id == course_id for batch in student_batches)
