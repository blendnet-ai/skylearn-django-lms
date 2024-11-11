from practice.providers.timezone import TimeZone

from practice.models import UserAttemptedQuestionResponse
from data_repo.models import QuestionBank
from django.db.models import Count

class QuestionHistoryHelper:

    type_name_mapping = {
        QuestionBank.QuestionType.IELTS: "IELTS",
        QuestionBank.QuestionType.INTERVIEW_PREP: 'Interview',
        QuestionBank.QuestionType.USER_CUSTOM_QUESTION: "Custom",
    }

    @staticmethod
    def get_user_question_history(user_id, question_type=None):
        """
        This function retrieves the question history for a specific user.

        Args:
            user_id (str): The user's ID.
            question_type (str, optional): The type of question. Defaults to None.
        Returns:
            list: A list of dictionaries containing the question id, attempted timestamp, and test name.
        """
        if question_type == 'IP':
            return QuestionHistoryHelper.get_interview_question_response(user_id)
        return QuestionHistoryHelper.get_other_question_response(user_id) if question_type else QuestionHistoryHelper.get_all_question_response(user_id)

    @staticmethod
    def get_interview_question_response(user_id):
        """
        Get the response for the latest interview questions attempted by a user.

        Args:
            user_id (int): The id of the user.

        Returns:
            list: A list of dictionaries containing the question id, attempted timestamp,
                and the test name for each attempt.
        """
        # Query the latest interview question attempts by the user
        interview_question_attempt = UserAttemptedQuestionResponse.objects.filter(
            user_question_attempt__user_id=user_id,
            user_question_attempt__attempt_status='AC',
            question_type=QuestionBank.QuestionType.INTERVIEW_PREP
        ).order_by('-created_at')

        interview_question_attempt_count = interview_question_attempt.count()

        # Generate the response list
        response_list = [
            {
                "question_id": str(attempt.id),
                # Format the timestamp to a specific format
                "attempted_timestamp": TimeZone.change_timezone(
                    attempt.created_at).strftime('%d %b %y %I:%M %p'),
                # Generate the test name
                "test_name": f"Interview #{interview_question_attempt_count - index}",
            }
            for index, attempt in enumerate(interview_question_attempt)
        ]

        return response_list

    @staticmethod
    def get_other_question_response(user_id):
        """
        Fetches the response of other question attempts for a given user.
        Args:
            user_id (int): The user id for which to fetch the attempts.
        Returns:
            list: A list of dictionaries containing question attempt details.
        """
        # Fetch other question attempts for the user
        other_question_attempt = UserAttemptedQuestionResponse.objects.filter(
            user_question_attempt__user_id=user_id,
            user_question_attempt__attempt_status='AC'
        ).exclude(question_type=QuestionBank.QuestionType.INTERVIEW_PREP).order_by('-created_at')

        # Count the number of other question attempts
        other_question_attempt_count = other_question_attempt.count()

        # Format the attempts into a list of dictionaries
        return [
            {
                "question_id": str(attempt.id),
                # Format the timestamp to a readable format
                "attempted_timestamp": TimeZone.change_timezone(attempt.created_at).strftime('%d %b %y %I:%M %p'),
                # Generate the test name
                "test_name": f"IELTS #{other_question_attempt_count - index}",
            }
            for index, attempt in enumerate(other_question_attempt)
        ]

    @staticmethod
    def get_all_question_response(user_id):
        """
        Fetches all question attempts for a given user.
        """
        # Initialize an empty list to store the attempt data
        attempt_data = []

        # Query the UserAttemptedQuestionResponse model to get all question attempts for the given user_id
        # Filter the attempts based on the user_id and attempt_status
        # Use prefetch_related to optimize the database queries
        # Sort the attempts in descending order based on the created_at field
        all_question_attempt = UserAttemptedQuestionResponse.objects.filter(
            user_question_attempt__user_id=user_id,
            user_question_attempt__attempt_status='AC'
        ).prefetch_related('user_question_attempt').order_by('-created_at')

        temp_type_count_dict = UserAttemptedQuestionResponse.objects.filter(
            user_question_attempt__user_id=user_id,
            user_question_attempt__attempt_status='AC'
        ).values('question_type').annotate(count=Count('id'))

        type_count_mapping = {item['question_type']: item['count'] for item in temp_type_count_dict}

        # Iterate over each question attempt
        for attempt in all_question_attempt:
            # Get the question_id and format it as a string
            question_id = str(attempt.id)

            # Get the created_at timestamp and convert it to the desired format
            attempted_timestamp = TimeZone.change_timezone(attempt.created_at).strftime('%d %b %y %I:%M %p')

            test_index = type_count_mapping[attempt.question_type]
            type_count_mapping[attempt.question_type] -= 1

            test_name = QuestionHistoryHelper.type_name_mapping.get(attempt.question_type, 'Other')

            # Create a dictionary with the attempt data and append it to the attempt_data list
            attempt_data.append(
                {
                    "question_id": question_id,
                    "attempted_timestamp": attempted_timestamp,
                    "test_name": f"{test_name} #{test_index}",
                }
            )

        # Return the attempt_data list
        return attempt_data
