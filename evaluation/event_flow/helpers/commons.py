from data_repo.models import QuestionBank

def get_eventflow_type_from_question_type(question_type):
    ef_type_map = {
        QuestionBank.QuestionType.IELTS: 'default',
        QuestionBank.QuestionType.INTERVIEW_PREP: 'interview_prep',
        QuestionBank.QuestionType.USER_CUSTOM_QUESTION: 'interview_prep',
    }
    return ef_type_map.get(question_type, 'default')