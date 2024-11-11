from data_repo.models import QuestionBank
from evaluation.event_flow.helpers.grammar import evaluate_grammar
from evaluation.event_flow.processors.base_grammar import BaseGrammar


class Grammar(BaseGrammar):

    def evaluate_with_specific_question_type(self, text, llm_object):
        return evaluate_grammar(text, llm_object, QuestionBank.QuestionType.IELTS)
