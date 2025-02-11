from data_repo.models import QuestionBank
from evaluation.event_flow.processors.base_grammar import BaseGrammar


class Grammar(BaseGrammar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question_type = QuestionBank.QuestionType.IELTS
