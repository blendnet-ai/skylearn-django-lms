import json
from django.core.cache import cache
from django.conf import settings
from django.apps import apps
from celery.exceptions import TimeoutError

from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, UserEvalQuestionAttempt
import logging

logger = logging.getLogger(__name__)

class EvaluationException(Exception):
    """Exception raised if data from evaluation task is None"""
    pass

class MockInterviewBehaviouralEvaluator(AssessmentEvaluator):    
    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def evaluate(self):
        if not self._should_start_evaluation():
            return
        QUALIFICATION_CRITERIA=60
        total_fluency_score = 0
        total_coherence_score=0
        total_emotion_score=0
        attempted_questions = UserEvalQuestionAttempt.objects.filter(
            assessment_attempt_id=self.assessment_attempt.assessment_id
        ).all()
        
        questions_data = self.assessment_attempt.question_list
        questions_evaluation_data = []
        eval_data = {'overall_summary': None, 'scores_summary': None, 'questions_evaluation_data': questions_evaluation_data,'total_fluency_score': total_fluency_score}  # Initialize as a dictionary
        question_count=0
        for sections in questions_data:
            for question_id in sections["questions"]:
                question_count+=1
                question_attempt = attempted_questions.filter(question_id=question_id).first()
                if question_attempt:
                    answer_type = question_attempt.question.answer_type
                    question_eval_data = question_attempt.eval_data
                    fluency_score = question_eval_data['fluency']['score']
                    total_fluency_score += fluency_score
                    coherence_score = question_eval_data['coherence']['score']
                    total_coherence_score += coherence_score
                    emotion_score=question_eval_data['coherence']['score']
                    total_emotion_score += emotion_score
                    ideal_response = question_eval_data['ideal_response']
                    data={
                        'fluency_score': fluency_score,
                        'coherence_score': coherence_score,
                        'emotion_score': emotion_score,
                        'question_text': ideal_response['question_text'],
                        'user_response': ideal_response['user_response'],
                        'ideal_response': ideal_response['ideal_response'],
                        'question_id': question_id
                    }
                    questions_evaluation_data.append(data)
        
        avg_fluency_score = total_fluency_score/question_count
        avg_coherence_score = total_coherence_score/question_count 
        avg_emotion_score = total_emotion_score/question_count
        
        self.assessment_attempt.eval_data['questions_evaluation_data'] = questions_evaluation_data
        self.assessment_attempt.eval_data['total_fluency_score'] = avg_fluency_score
        self.assessment_attempt.eval_data['total_coherence_score'] = avg_coherence_score
        self.assessment_attempt.eval_data['total_emotion_score'] = avg_emotion_score
        total_score = (avg_fluency_score + avg_coherence_score + avg_emotion_score)/3
        self.assessment_attempt.eval_data['total_score']=total_score
        if total_score>=QUALIFICATION_CRITERIA:
            self.assessment_attempt.eval_data['qualified']=True
        else:
            self.assessment_attempt.eval_data['qualified']=False
            
        self.assessment_attempt.save()
        
        # Trigger the Celery task
        self.generate_overall_summary_celery_task(self.assessment_attempt.eval_data,self.assessment_attempt.assessment_id)

    def generate_overall_summary_celery_task(self, eval_data,assessment_attempt_id):
            from evaluation.tasks import evaluate_behavioral_assessment
            task = evaluate_behavioral_assessment.delay(eval_data,assessment_attempt_id)
            
