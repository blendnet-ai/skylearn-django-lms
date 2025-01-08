from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt


class LogicalAssessmentEvaluator(AssessmentEvaluator):
    # MCQ_POINTS = 3
    # MCQ_INCORRECT_POINTS = -1
    MCQ_POINTS = 1
    MCQ_INCORRECT_POINTS = 0

    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def evaluate(self):
        if not self._should_start_evaluation():
            return

        score = 0
        max_score = 0
        correct_count = 0
        incorrect_count = 0
        not_attempted_count = 0
        overall_percentage = 0
        attempted_questions = UserEvalQuestionAttempt.objects.filter(
            assessment_attempt_id=self.assessment_attempt.assessment_id
        ).all()
        
        questions_data = self.assessment_attempt.question_list
        
        list_section_wise_score = []
        
        for sections in questions_data:
            section_wise_score = 0
            section_wise_max_score = 0
            section_wise_correct = 0
            section_wise_incorrect = 0
            section_wise_not_attempted = 0
            
            for question_id in sections["questions"]:
                question = Question.objects.filter(id=question_id).first()
                question_attempt = attempted_questions.filter(question_id=question_id).first()
                if question_attempt:
                    answer_type = question_attempt.question.answer_type
                    question_eval_data = question_attempt.eval_data
                    
                    if answer_type == int(Question.AnswerType.MCQ):
                        if question_eval_data["is_correct"]:
                            section_wise_score += LogicalAssessmentEvaluator.MCQ_POINTS
                            section_wise_correct += 1
                        else:
                            section_wise_incorrect += 1
                            section_wise_score += LogicalAssessmentEvaluator.MCQ_INCORRECT_POINTS
                            
                        section_wise_max_score += LogicalAssessmentEvaluator.MCQ_POINTS
                        
                    if answer_type == int(Question.AnswerType.MMCQ):
                        for item in question_eval_data:
                            if item["is_correct"]:
                                section_wise_score += LogicalAssessmentEvaluator.MCQ_POINTS
                                section_wise_correct += 1
                            else:
                                section_wise_incorrect += 1
                                section_wise_score += LogicalAssessmentEvaluator.MCQ_INCORRECT_POINTS
                                
                            section_wise_max_score += LogicalAssessmentEvaluator.MCQ_POINTS
                        no_of_questions = len(question.question_data["questions"])
                        if len(question_eval_data) < no_of_questions:
                            section_wise_not_attempted += no_of_questions - len(question_eval_data)
                        
                        
                else:
                    if question.answer_type == int(Question.AnswerType.MCQ):
                        section_wise_not_attempted += 1
                        section_wise_max_score += LogicalAssessmentEvaluator.MCQ_POINTS
                    if question.answer_type == int(Question.AnswerType.MMCQ):
                        no_of_questions = len(question.question_data["questions"])
                        section_wise_not_attempted += no_of_questions
                        section_wise_max_score += LogicalAssessmentEvaluator.MCQ_POINTS*no_of_questions

            score += section_wise_score
            max_score += section_wise_max_score
            correct_count += section_wise_correct
            incorrect_count += section_wise_incorrect
            not_attempted_count += section_wise_not_attempted
            
            normalized_score = round((section_wise_score * 100) / section_wise_max_score, 2) if section_wise_score > 0 else 0
            overall_percentage += normalized_score
            emoji = "shapes"
            if sections["section"] == Question.SubCategory.NON_VERBAL.label:
                emoji = "messages"
            elif sections["section"] == Question.SubCategory.DATA_INTERPRETATION.label:
                emoji = "chart"
            elif sections["section"] == Question.SubCategory.NUMERICAL.label:
                emoji = "math"
                
            list_section_wise_score.append({
                "name": sections["section"],
                "correct": section_wise_correct,
                "incorrect": section_wise_incorrect,
                "not_attempted": section_wise_not_attempted,
                "percentage" : normalized_score,
                "emoji": emoji,
            })
        
        overall_normalized_score = round(overall_percentage/ len(questions_data), 1)
        additional_data = {
            "correct": correct_count,
            "incorrect": incorrect_count,
            "not_attempted": not_attempted_count,
            "sections": list_section_wise_score,
        }

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
            "additional_data": additional_data,
            "percentage": overall_normalized_score,
            "max_score": max_score,
            "total_score": score,
            "performance_tag": performance_tag
        }
     
        self.assessment_attempt.eval_data = eval_data

        self.assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        self.assessment_attempt.evaluation_triggered = True

        self.assessment_attempt.save()
