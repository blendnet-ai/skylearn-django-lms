import json
from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt


class PersonalityAssessmentEvaluator(AssessmentEvaluator):

    def _get_types_array(types_str: str):
        types = types_str.split(",")
        return types

    def _get_highest_score_types(scores):
        pairs = ["EI", "SN", "TF", "JP"]

        selected_types = []
        # Iterate through each pair
        for pair in pairs:
            # Get the scores for each letter in the pair
            letter1, letter2 = pair
            score1 = scores[letter1]
            score2 = scores[letter2]

            # Select the letter with the highest score
            selected_letter = letter1 if score1 > score2 else letter2
            selected_types.append(selected_letter)

        return selected_types

    def __init__(self, assessment_attempt: AssessmentAttempt):
        super().__init__(assessment_attempt)

    def evaluate(self):
        if not self._should_start_evaluation():
            return
        
        full_forms = {"E": "Extroverted", "I": "Introverted", "S": "Sensing", "N": "Intuitive", "T": "Thinking", "F": "Feeling", "J": "Judging", "P": "Perceiving"}
        scores = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
        
        attempted_questions = UserEvalQuestionAttempt.objects.filter(
            assessment_attempt_id=self.assessment_attempt.assessment_id
        ).all()
        questions_data = self.assessment_attempt.question_list
        for sections in questions_data:
            for question_id in sections["questions"]:

                question_attempt = attempted_questions.filter(question_id=question_id).first()

                if question_attempt:
                    question_data = question_attempt.question.question_data

                    # Get the types (eg E,I) in a array
                    types = PersonalityAssessmentEvaluator._get_types_array(
                        question_data["type"]
                    )

                    # If the mcq answer was 0 (option a) it will add to the 0th type and to 1st type for mcq answer 1
                    # scores[types[question_attempt.mcq_answer]] += 1
                    scores[types[question_attempt.mcq_answer]] += 1
                    question_attempt.status = UserEvalQuestionAttempt.Status.EVALUATED
                    question_attempt.save()

        highest_score_types = PersonalityAssessmentEvaluator._get_highest_score_types(
            scores
        )
        score_text = "".join(highest_score_types)
        short_description = "Personality Type - " + " ".join(full_forms[type] for type in highest_score_types)
        eval_data = {"highest_score_types": highest_score_types, "score_text": score_text, "short_description": short_description}

        self.assessment_attempt.eval_data = eval_data
        self.assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        self.assessment_attempt.evaluation_triggered = True

        self.assessment_attempt.save()
