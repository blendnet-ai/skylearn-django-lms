import random

from data_repo.models import QuestionBank


class QuestionBankProvider:
    @staticmethod
    def get_random_questions(num_questions=1, question_type=None):
        """
        Get a specified number of random practice questions
        """

        questions = QuestionBank.objects.filter(is_active=True)
        if question_type:
            questions = questions.filter(type=question_type)

        if questions.exists():
            random_questions = random.sample(list(questions),
                                             min(num_questions, len(questions)))
            return random_questions
        else:
            return []

    @staticmethod
    def get_question(question_id):
        """
        Get a specific practice question by ID
        """
        try:
            question = QuestionBank.objects.get(pk=question_id)
            return question
        except QuestionBank.DoesNotExist:
            return None
