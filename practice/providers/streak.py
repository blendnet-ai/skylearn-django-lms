from datetime import datetime, timedelta, date

from practice.models import UserQuestionAttempt
from django.core.exceptions import ObjectDoesNotExist


class StreakHelper:
    @staticmethod
    def get_last_attempt(user_id):
        """
            Retrieves the last attempt made by a user.

            Args:
                user_id (int): The ID of the user.

            Returns:
                UserQuestionAttempt or None: The last attempt made by the user, or None if no attempts exist.
        """
        try:
            filter_conditions = {
                'user_id': user_id,
                'attempt_status': UserQuestionAttempt.AttemptStatus.ATTEMPT_COMPLETED
            }
            last_attempt = UserQuestionAttempt.objects.filter(**filter_conditions).order_by('created_at').last()
            return last_attempt
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def has_attempted_yesterday (user_id):
        """
            Check if a user has made any question attempts yesterday.

            Parameters:
                user_id (int): The ID of the user to check.

            Returns:
                bool: True if the user has made attempts yesterday, False otherwise.
        """
        yesterday_midnight = StreakHelper.get_yesterday_midnight()
        filter_conditions = {
            'user_id': user_id,
            'created_at__gte': yesterday_midnight,
            'attempt_status': UserQuestionAttempt.AttemptStatus.ATTEMPT_COMPLETED
        }
        return UserQuestionAttempt.objects.filter(**filter_conditions).exists()

    @staticmethod
    def get_latest_streak(user_id):
        """
            Updates the streak for a given user.

            Parameters:
                user_id (int): The ID of the user.

            Returns:
                int: The updated daily streak for the user.
        """
        last_attempt = StreakHelper.get_last_attempt(user_id)
        if last_attempt:
            if last_attempt.created_at.date() == date.today():
                return last_attempt.daily_streak
            elif StreakHelper.has_attempted_yesterday(user_id):
                return last_attempt.daily_streak + 1
        return 1  # Set daily streak to 1 for new users or users with no previous attempts

    @staticmethod
    def get_last_streak(user_id):
        if StreakHelper.has_attempted_yesterday(user_id):
            last_attempt = StreakHelper.get_last_attempt(user_id)
            return last_attempt.daily_streak
        else:
            return 0

    @staticmethod
    def get_todays_date():
        # TODO: Make this timezone aware
        today = date.today()
        return today

    @staticmethod
    def get_yesterday_midnight():
        yesterday = StreakHelper.get_todays_date() - timedelta(days=1)
        # This will set yesterday time to 00:00:00, i.e., midnight
        yesterday_midnight = datetime.combine(yesterday, datetime.min.time())
        return yesterday_midnight
