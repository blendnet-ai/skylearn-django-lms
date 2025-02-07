from Feedback.repositories import FeedbackFormRepository
from course.repositories import BatchRepository
from course.usecases import CourseUseCase

class FeedbackFormUsecase:
    @staticmethod
    def get_form_by_name(name):
        feedback_form = FeedbackFormRepository.get_by_name(name=name)
        return {"form": feedback_form.data, "id": feedback_form.id}
    
    @staticmethod
    def get_feedback_value(filled_form, field_name):
        filled_form = filled_form[0]
        fields = filled_form.get("fields", [])
        for field in fields:
            if field.get("name", "") == field_name:
                return field.get("value", "")

class FeedbackResponseUsecase:
    @staticmethod
    def get_forms_status(user, current_date):
        courses, role = CourseUseCase.get_courses_for_student_or_lecturer(user)
        user_id = user.id
        
        response_data = []
        
        for course in courses:
            course_data = {
                "course_id": course.get("id"),
                "course_name": course.get("title"),
                "course_code": course.get("code"),
                "batch": course.get("batch_id"),
                "forms_data":None
            }
            
            # Get batches for this course
            batch_id = course.get("batch_id")
            if batch_id:
                # Get forms status for this batch
                forms_status = FeedbackFormRepository.get_forms_by_user_and_batch(
                    user_id, 
                    batch_id, 
                    current_date
                )
                
                forms_data = {
                    "forms": forms_status
                }
                course_data['action_required'] = FeedbackFormRepository.check_if_any_pending_mandatory_forms(user_id, batch_id, current_date)
                course_data["forms_data"]=forms_data

            

            response_data.append(course_data)
            
        return response_data
    
    @staticmethod
    def check_if_any_pending_mandatory_forms(user_id, batch_id, current_date):
        return FeedbackFormRepository.check_if_any_pending_mandatory_forms(user_id, batch_id, current_date)
