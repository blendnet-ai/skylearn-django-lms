import json
from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt

class LanguageAssessmentEvaluatorOld(AssessmentEvaluator):#new class with my code
    
    MCQ_POINTS = 3
    MCQ_INCORRECT_POINTS = -1
    SPEAKING_POINTS = 100
    WRITING_POINTS = 100
    
    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def evaluate(self):
        if not self._should_start_evaluation():
            return

        overall_score = 0
        overall_max_score = 0

        attempted_questions = UserEvalQuestionAttempt.objects.filter(
            assessment_attempt_id=self.assessment_attempt.assessment_id
        ).all()
        
        questions_data = self.assessment_attempt.question_list

        list_section_wise_score = []
        
        for sections in questions_data:
            
            section_wise_score = 0
            section_wise_max_score = 0
            grammar_score = 0
            coherence_score = 0
            vocab_score = 0
            fluency_score = 0
            pronunciation_score = 0
            sentiment_score = 0
            
            for question_id in sections["questions"]:
                
                # TODO Attempted_questions should be a python data structure
                question_attempt = attempted_questions.filter(question_id=question_id).first()
                if question_attempt:
                    answer_type = question_attempt.question.answer_type
                    question_eval_data = question_attempt.eval_data

                    sub_category = question_attempt.question.sub_category

                    if sub_category == int(Question.SubCategory.LISTENING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.MMCQ):
                            for mcq_eval_data in question_eval_data:
                                section_wise_score += (
                                    LanguageAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LanguageAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                                section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS


                    elif sub_category == int(Question.SubCategory.SPEAKING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.VOICE):
                            section_wise_score += question_eval_data["final_score"]
                            grammar_score += question_eval_data["grammar"].get('score', None)
                            coherence_score += question_eval_data["coherence"].get('score', None)
                            vocab_score += question_eval_data["vocab"].get('score', None)
                            pronunciation_score += question_eval_data["pronunciation"].get('score', None)
                            fluency_score += question_eval_data["fluency"].get('score', None)
                            sentiment_score += question_eval_data["sentiment"].get('score', None)

                            section_wise_max_score += LanguageAssessmentEvaluator.SPEAKING_POINTS

                    elif sub_category == int(Question.SubCategory.WRITING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.SUBJECTIVE):
                            section_wise_score += question_eval_data["final_score"]
                            grammar_score += question_eval_data["grammar"].get('score', None)
                            coherence_score += question_eval_data["coherence"].get('score', None)
                            vocab_score += question_eval_data["vocab"].get('score', None)
                            section_wise_max_score += LanguageAssessmentEvaluator.WRITING_POINTS                            
                            
                    elif sub_category == int(Question.SubCategory.RC) and question_eval_data:
                        if answer_type == int(Question.AnswerType.MMCQ):
                            for mcq_eval_data in question_eval_data:
                                section_wise_score += (
                                    LanguageAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LanguageAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                                section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS
                                                                
            
                else:
                    question = Question.objects.filter(id=question_id).first()
                    sub_category = question.sub_category
                    if sub_category == int(Question.SubCategory.LISTENING):
                        section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                    elif sub_category == int(Question.SubCategory.SPEAKING):
                        section_wise_max_score += LanguageAssessmentEvaluator.SPEAKING_POINTS
                    elif sub_category == int(Question.SubCategory.WRITING):
                        section_wise_max_score += LanguageAssessmentEvaluator.WRITING_POINTS
                    elif sub_category == int(Question.SubCategory.RC):
                        section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                        
            num_questions = len(sections["questions"])
            overall_score += section_wise_score
            overall_max_score += section_wise_max_score
            normalized_section_wise_score = round((section_wise_score * 100) / section_wise_max_score, 2) if section_wise_score > 0 else 0
            emoji = "happy"
            if sections["section"] == Question.SubCategory.WRITING.label:
                emoji = "edit"
            elif sections["section"] == Question.SubCategory.RC.label:
                emoji = "book-saved"
            elif sections["section"] == Question.SubCategory.LISTENING.label:
                emoji = "listen"

            section_dict = {
                "name": sections["section"],
                "percentage": normalized_section_wise_score,
                "emoji": emoji,
            }
            
            if sections["section"] in ["Speaking", "Writing"]:
                section_dict["sections"] = []
                if grammar_score:
                    section_dict["sections"].append({"name": "Grammar", "percentage": grammar_score/num_questions})
                if coherence_score:
                    section_dict["sections"].append({"name": "Coherence", "percentage": coherence_score/num_questions})
                if vocab_score:
                    section_dict["sections"].append({"name": "Vocabulary", "percentage": vocab_score/num_questions})
                if fluency_score:
                    section_dict["sections"].append({"name": "Fluency", "percentage": fluency_score/num_questions})
                if pronunciation_score:
                    section_dict["sections"].append({"name": "Pronunciation", "percentage": pronunciation_score/num_questions})
                if sentiment_score:
                    section_dict["sections"].append({"name": "Sentiment", "percentage": sentiment_score/num_questions})
                
            list_section_wise_score.append(section_dict)
            
        # for loop over the normalized scores of each section and calculate average
        overall_percentage = 0
        for section in list_section_wise_score:
            if section.get("percentage"):
                overall_percentage += section["percentage"]
                
        overall_normalized_score = round(overall_percentage / len(list_section_wise_score), 2) if overall_percentage > 0 else 0
        performance_tag = "OUTSTANDING"
        if overall_normalized_score >= 70 and overall_normalized_score < 85:
            performance_tag = "COMPETENT"
        elif overall_normalized_score >= 55:
            performance_tag = "GOOD"
        elif overall_normalized_score >= 40:
            performance_tag = "AVERAGE"
        elif overall_normalized_score < 40:
            performance_tag = "UNSATISFACTORY"
            

        eval_data = {
            "percentage": overall_normalized_score,
            "additional_data": {"sections": list_section_wise_score},
            "performance_tag": performance_tag
        }

        self.assessment_attempt.eval_data = eval_data

        self.assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        self.assessment_attempt.evaluation_triggered = True

        self.assessment_attempt.save()


class LanguageAssessmentEvaluator(AssessmentEvaluator):
    
    MCQ_POINTS = 1
    MCQ_INCORRECT_POINTS = 0
    SPEAKING_POINTS = 100
    WRITING_POINTS = 100

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
                                    LanguageAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LanguageAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                                listening_max_score += LanguageAssessmentEvaluator.MCQ_POINTS


                    elif sub_category == int(Question.SubCategory.SPEAKING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.VOICE):
                            speaking_score += question_eval_data["final_score"]
                            speaking_fluency_score += question_eval_data["fluency"].get('score', None)
                            speaking_vocab_score += question_eval_data["vocab"].get('score', None)
                            speaking_coherence_score += question_eval_data["coherence"].get('score', None)
                            speaking_pronunciation_score += question_eval_data["pronunciation"].get('score', None)
                            speaking_grammar_score += question_eval_data["grammar"].get('score', None)
                            speaking_sentiment_score += question_eval_data["sentiment"].get('score', None)
                            speaking_max_score += LanguageAssessmentEvaluator.SPEAKING_POINTS

                    elif sub_category == int(Question.SubCategory.RC) and question_eval_data:
                        if answer_type == int(Question.AnswerType.MMCQ):
                            for mcq_eval_data in question_eval_data:
                                reading_score += (
                                    LanguageAssessmentEvaluator.MCQ_POINTS
                                    if mcq_eval_data["is_correct"]
                                    else LanguageAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                )
                            reading_max_score += LanguageAssessmentEvaluator.MCQ_POINTS

                    elif sub_category == int(Question.SubCategory.WRITING) and question_eval_data:
                        if answer_type == int(Question.AnswerType.SUBJECTIVE):
                            writing_score += question_eval_data["final_score"]
                            writing_grammar_score += question_eval_data["grammar"].get('score', None)
                            writing_coherence_score += question_eval_data["coherence"].get('score', None)
                            writing_vocab_score += question_eval_data["vocab"].get('score', None)                           
                            writing_max_score += LanguageAssessmentEvaluator.WRITING_POINTS

                                                                
            
                else:
                    question = Question.objects.filter(id=question_id).first()
                    sub_category = question.sub_category
                    if sub_category == int(Question.SubCategory.LISTENING):
                        section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                    elif sub_category == int(Question.SubCategory.SPEAKING):
                        section_wise_max_score += LanguageAssessmentEvaluator.SPEAKING_POINTS
                    elif sub_category == int(Question.SubCategory.WRITING):
                        section_wise_max_score += LanguageAssessmentEvaluator.WRITING_POINTS
                    elif sub_category == int(Question.SubCategory.RC):
                        section_wise_max_score += LanguageAssessmentEvaluator.MCQ_POINTS * len(question.question_data.get("questions", []))
                        
            
       
        # Convert MCQ-based scores (Listening and Reading) to 0-10 scale
        listening_score_10 = (listening_score / listening_max_score * 10) if listening_max_score else 0
        reading_score_10 = (reading_score / reading_max_score * 10) if reading_max_score else 0
        
        # Convert Speaking scores to 0-10 scale
        speaking_score_10 = (speaking_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_fluency_10 = (speaking_fluency_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_vocab_10 = (speaking_vocab_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_coherence_10 = (speaking_coherence_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_pronunciation_10 = (speaking_pronunciation_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_grammar_10 = (speaking_grammar_score / speaking_max_score * 10) if speaking_max_score else 0
        speaking_sentiment_10 = (speaking_sentiment_score / speaking_max_score * 10) if speaking_max_score else 0
        
        # Convert Writing scores to 0-10 scale
        writing_score_10 = (writing_score / writing_max_score * 10) if writing_max_score else 0
        writing_grammar_10 = (writing_grammar_score / writing_max_score * 10) if writing_max_score else 0
        writing_coherence_10 = (writing_coherence_score / writing_max_score * 10) if writing_max_score else 0
        writing_vocab_10 = (writing_vocab_score / writing_max_score * 10) if writing_max_score else 0

        # Calculate normalized averages on 0-10 scale
        overall_score_10 = (listening_score_10 + speaking_score_10 + reading_score_10 + writing_score_10) / 4
        speaking_normalized_10 = (speaking_score_10 + speaking_fluency_10 + speaking_vocab_10 + 
                                speaking_coherence_10 + speaking_pronunciation_10 + speaking_grammar_10 + 
                                speaking_sentiment_10) / 7
        writing_normalized_10 = (writing_score_10 + writing_grammar_10 + writing_coherence_10 + writing_vocab_10) / 4

        eval_data = {
            "total_score": round((listening_score_10 + speaking_score_10 + reading_score_10 + writing_score_10) / 4, 1),
            "max_score": 10.0,
            "percentage": round(((listening_score_10 + speaking_score_10 + reading_score_10 + writing_score_10) / 4) * 10, 1),
            "performance_overview": {
                "feedback": "You have done well in the assessment. Keep up the good work.",
                "score": round(overall_score_10, 1)
            },
            "performance_metrics": [
                {"category": "Speaking", "score": round(speaking_normalized_10, 1)},
                {"category": "Listening", "score": round(listening_score_10, 1)},
                {"category": "Writing", "score": round(writing_normalized_10, 1)},
                {"category": "Reading", "score": round(reading_score_10, 1)}
            ],
            "sections": [
                {
                    "name": "Speaking",
                    "metrics": [
                        {
                            "name": "Fluency",
                            "total_score": 10,
                            "obtained_score": round(speaking_fluency_10, 1)
                        },
                        {
                            "name": "Vocab",
                            "total_score": 10,
                            "obtained_score": round(speaking_vocab_10, 1)
                        },
                        {
                            "name": "Coherence",
                            "total_score": 10,
                            "obtained_score": round(speaking_coherence_10, 1)
                        },
                        {
                            "name": "Pronunciation",
                            "total_score": 10,
                            "obtained_score": round(speaking_pronunciation_10, 1)
                        },
                        {
                            "name": "Grammar",
                            "total_score": 10,
                            "obtained_score": round(speaking_grammar_10, 1)
                        },
                        {
                            "name": "Emotion",
                            "total_score": 10,
                            "obtained_score": round(speaking_sentiment_10, 1)
                        }
                    ]
                },
                {
                    "name": "Listening",
                    "metrics": [
                        {
                            "name": "Correct Questions",
                            "total_score": 10,
                            "obtained_score": round(listening_score_10, 1)
                        },
                        {
                            "name": "Incorrect Questions",
                            "total_score": 10,
                            "obtained_score": round(10 - listening_score_10, 1)
                        }
                    ]
                },
                {
                    "name": "Writing",
                    "metrics": [
                        {
                            "name": "Vocab",
                            "total_score": 10,
                            "obtained_score": round(writing_vocab_10, 1)
                        },
                        {
                            "name": "Coherence",
                            "total_score": 10,
                            "obtained_score": round(writing_coherence_10, 1)
                        },
                        {
                            "name": "Grammar",
                            "total_score": 10,
                            "obtained_score": round(writing_grammar_10, 1)
                        }
                    ]
                },
                {
                    "name": "Reading",
                    "metrics": [
                        {
                            "name": "Correct Questions",
                            "total_score": 10,
                            "obtained_score": round(reading_score_10, 1)
                        },
                        {
                            "name": "Incorrect Questions",
                            "total_score": 10,
                            "obtained_score": round(10 - reading_score_10, 1)
                        }
                    ]
                }
            ]
        }
        
        self.assessment_attempt.eval_data = eval_data
        self.assessment_attempt.save()
        # Trigger the Celery task
        self.generate_overall_summary_celery_task(self.assessment_attempt.eval_data,self.assessment_attempt.assessment_id)

    def generate_overall_summary_celery_task(self, eval_data,assessment_attempt_id):
            from evaluation.tasks import evaluate_lsrw_assessment
            task = evaluate_lsrw_assessment.delay(eval_data,assessment_attempt_id)


