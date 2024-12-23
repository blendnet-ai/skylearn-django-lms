import json
from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt

class LSRWAssessmentEvaluator(AssessmentEvaluator):
    
    MCQ_POINTS = 1
    MCQ_INCORRECT_POINTS = 0
    SPEAKING_POINTS = 10
    WRITING_POINTS = 10
    
    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def evaluate(self):
        if not self._should_start_evaluation():
            return

        overall_score = 0
        overall_max_score = 0
        
        speaking_grammar_score = 0
        speaking_coherence_score = 0
        speaking_vocab_score = 0
        speaking_fluency_score = 0
        speaking_pronunciation_score = 0
        speaking_sentiment_score = 0

        writing_grammar_score = 0
        writing_coherence_score = 0
        writing_vocab_score = 0
      
        attempted_questions = UserEvalQuestionAttempt.objects.filter(
            assessment_attempt_id=self.assessment_attempt.assessment_id
        ).all()
        
        questions_data = self.assessment_attempt.question_list

        list_section_wise_score = []
        #Answer type
        #3 - speaking
        #0 - listining
        #1 - reading comperehension
        #2 - writing
        listening_score=0
        listening_max_score=0
        reading_score=0
        reading_max_score=0
        writing_score=0
        writing_max_score=0
        speaking_score=0
        speaking_max_score=0
        for sections in questions_data:
            for question_id in sections["questions"]:
                question_attempt = attempted_questions.filter(question_id=question_id).first()
                if question_attempt:
                    answer_type = question_attempt.question.answer_type
                    question_eval_data = question_attempt.eval_data

                    sub_category = question_attempt.question.sub_category

                    if sub_category == int(Question.SubCategory.LISTENING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.MMCQ):
                            for mcq_eval_data in question_eval_data:
                                listening_score += (
                                    LSRWAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LSRWAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                                listening_max_score += LSRWAssessmentEvaluator.MCQ_POINTS


                    elif sub_category == int(Question.SubCategory.SPEAKING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.VOICE):
                            speaking_score += question_eval_data["final_score"]
                            speaking_fluency_score += question_eval_data["fluency"].get('score', None)
                            speaking_vocab_score += question_eval_data["vocab"].get('score', None)
                            speaking_coherence_score += question_eval_data["coherence"].get('score', None)
                            speaking_pronunciation_score += question_eval_data["pronunciation"].get('score', None)
                            speaking_grammar_score += question_eval_data["grammar"].get('score', None)
                            speaking_sentiment_score += question_eval_data["sentiment"].get('score', None)
                            speaking_max_score += LSRWAssessmentEvaluator.SPEAKING_POINTS

                    elif sub_category == int(Question.SubCategory.RC) and question_eval_data:
                        if answer_type == int(Question.AnswerType.MMCQ):
                            for mcq_eval_data in question_eval_data:
                                reading_score += (
                                    LSRWAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LSRWAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                            reading_max_score += LSRWAssessmentEvaluator.MCQ_POINTS

                    elif sub_category == int(Question.SubCategory.WRITING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.SUBJECTIVE):
                            writing_score += question_eval_data["final_score"]
                            writing_grammar_score += question_eval_data["grammar"].get('score', None)
                            writing_coherence_score += question_eval_data["coherence"].get('score', None)
                            writing_vocab_score += question_eval_data["vocab"].get('score', None)                            
                            writing_max_score += LSRWAssessmentEvaluator.WRITING_POINTS

                                                                
            
                else:
                    question = Question.objects.filter(id=question_id).first()
                    sub_category = question.sub_category
                    if sub_category == int(Question.SubCategory.LISTENING):
                        section_wise_max_score += LSRWAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                    elif sub_category == int(Question.SubCategory.SPEAKING):
                        section_wise_max_score += LSRWAssessmentEvaluator.SPEAKING_POINTS
                    elif sub_category == int(Question.SubCategory.WRITING):
                        section_wise_max_score += LSRWAssessmentEvaluator.WRITING_POINTS
                    elif sub_category == int(Question.SubCategory.RC):
                        section_wise_max_score += LSRWAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                        
            
       
            
        overall_normalized_score = (listening_score+speaking_score+reading_score+writing_score)/4
        overall_max_score = (listening_max_score+speaking_max_score+reading_max_score+writing_max_score)/4
        speaking_normalized_score = (speaking_score+speaking_fluency_score+speaking_vocab_score+speaking_coherence_score+speaking_pronunciation_score+speaking_grammar_score+speaking_sentiment_score)/7
        writing_normalized_score = (writing_score+writing_grammar_score+writing_coherence_score+writing_vocab_score)/4
        reading_normalized_score = reading_score
        listening_normalized_score = listening_score
        summary=""
        eval_data = {
            "performance_overview": {
                "feedback": "You have done well in the assessment. Keep up the good work.",
                "score": round((overall_normalized_score/overall_max_score) * 10, 1)
            },
            "performance_metrics": [
                {"category": "Speaking", "score": round((speaking_normalized_score/speaking_max_score) * 10, 1)},
                {"category": "Listening", "score": round((listening_normalized_score/listening_max_score) * 10, 1)},
                {"category": "Writing", "score": round((writing_normalized_score/writing_max_score) * 10, 1)},
                {"category": "Reading", "score": round((reading_normalized_score/reading_max_score) * 10, 1)}
            ],
            "sections": [
                {
                    "name": "Speaking",
                    "metrics": [
                        {
                            "name": "Fluency",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_fluency_score
                        },
                        {
                            "name": "Vocab",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_vocab_score
                        },
                        {
                            "name": "Coherence",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_coherence_score
                        },
                        {
                            "name": "Pronunciation",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_pronunciation_score
                        },
                        {
                            "name": "Grammar",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_grammar_score
                        },
                        {
                            "name": "Emotion",
                            "total_score": speaking_max_score,
                            "obtained_score": speaking_sentiment_score
                        }
                    ]
                },
                {
                    "name": "Listening",
                    "metrics": [
                        {
                            "name": "Correct Questions",
                            "total_score": listening_max_score,
                            "obtained_score": listening_score
                        },
                        {
                            "name": "Incorrect Questions",
                            "total_score": listening_max_score,
                            "obtained_score": listening_max_score - listening_score
                        }
                    ]
                },
                {
                    "name": "Writing",
                    "metrics": [
                        {
                            "name": "Vocab",
                            "total_score": writing_max_score,
                            "obtained_score": writing_vocab_score
                        },
                        {
                            "name": "Coherence",
                            "total_score": writing_max_score,
                            "obtained_score": writing_coherence_score
                        },
                        {
                            "name": "Grammar",
                            "total_score": writing_max_score,
                            "obtained_score": writing_grammar_score
                        }
                    ]
                },
                {
                    "name": "Reading",
                    "metrics": [
                        {
                            "name": "Correct Questions",
                            "total_score": reading_max_score,
                            "obtained_score": reading_score
                        },
                        {
                            "name": "Incorrect Questions",
                            "total_score": reading_max_score,
                            "obtained_score": reading_max_score - reading_score
                        }
                    ]
                }
            ]
        }

        self.assessment_attempt.eval_data = eval_data

        self.assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        self.assessment_attempt.evaluation_triggered = True

        self.assessment_attempt.save()
