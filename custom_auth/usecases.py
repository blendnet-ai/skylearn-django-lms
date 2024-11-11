from datetime import datetime
from django.utils import timezone
from datetime import timedelta
import logging
import firebase_admin

#from InstituteConfiguration.repositories import InstituteRepository
from custom_auth.repositories import UserProfileRepository
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.services.sendgrid_service import SendgridService

from data_repo.repositories import ConfigMapRepository
from evaluation.management.register.utils import Utils
from evaluation.repositories import AssessmentAttemptRepository

#from DoubtSolving.usecases import UserMappingUseCase
import re
from datetime import timedelta
import datetime
import pytz

logger = logging.getLogger(__name__)


class BetaUserlistUsecase:
    @staticmethod
    def mark_onboarding_complete_for_user_if_not(*, email: str, user_id: str):
        existing_profile = UserProfileRepository.fetch_user_data(user_id)
        if not existing_profile.get('onboarding_status'):
            UserProfileRepository.set_onboarding_complete(user_id)
    
    @staticmethod
    def mark_onboarding_complete_if_whitelisted_user(*, email: str, user_id: str):
        whitelisted_user_emails = ConfigMapRepository.get_config_by_tag(
            tag=ConfigMapRepository.WHITELISTED_USER_EMAILS)
        if email in whitelisted_user_emails:
            logger.info(
                f"Marking user email - {email},id={user_id} as on-boarding completed.")
            UserProfileRepository.set_onboarding_complete(user_id)

    # @staticmethod
    # def mark_onboarding_complete_and_assign_institue_if_in_institue_student_list(*, email: str, user_id: str):
    #     institutes = InstituteRepository.get_all()
    #     for institute in institutes:
    #         if email in institute.student_emails:
    #             logger.info(
    #                 f"User email - {email}, id={user_id} found in institute {institute.name} student list.")
    #             UserProfileRepository.set_onboarding_complete(user_id)
    #             UserProfileRepository.set_institute(user_id, institute)

    # @staticmethod
    # def assign_institute_based_on_email_domain(*,email: str, user_id:str):
    #     print(email,user_id)
    #     pattern = r'@(.*)'
    #     match = re.search(pattern, email)
    #     if match:
    #         domain = match.group(1)
    #         institute=InstituteRepository.check_for_domain(domain)
    #         if institute:
    #             UserProfileRepository.set_institute(user_id,institute)
    #         else:
    #             logging.info(f"No institute found for domain :{domain}")


class ActivityDataUseCase:
    @staticmethod
    def get_and_update_activity_data(user_id: str):
        today = timezone.now().date()

        yesterday = (today - timedelta(days=1))

        user_profile = UserProfileRepository.get(user_id=user_id)

        if not AssessmentAttemptRepository.does_attempts_exist_for_date(today) and not AssessmentAttemptRepository.does_attempts_exist_for_date(yesterday):
            # if there are not attempts completed on Today or Yesterday, then break the steak
            user_profile.daily_streak = 0
            user_profile.save()

        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        activity_status = [False] * 7

        current_date = start_of_week
        while current_date <= end_of_week:
            day_of_week = (current_date - start_of_week).days
            current_date_str = current_date.isoformat()

            if current_date_str in user_profile.activity_dates:
                activity_status[day_of_week] = True
            current_date += timedelta(days=1)

        longest_streak = user_profile.longest_streak
        current_streak = user_profile.daily_streak

        activity_data = {
            'longest_streak': longest_streak,
            'current_streak': current_streak,
            'activity_status': activity_status
        }
        return activity_data

class SignUpUsecase:

    @staticmethod
    def sign_up(email: str):
        password = Utils.generate_random_password()

        try:
            CustomAuth.create_user(email=email, password=password)
        except firebase_admin.auth.EmailAlreadyExistsError:
            return "Email already exists, please try sign in."
        except ValueError:
            return "Invalid email."

        SendgridService.send_password_email(email=email, password=password)

        return None

# class DoubtSolvingTokenUseCase():
#     @staticmethod
#     def create_or_get_token(user_id,api_key):
#         user_profile = UserProfileRepository.get(user_id=user_id)
#         is_token_valid=False
#         if user_profile.doubt_solving_mapping_created:
#             if not is_token_valid:
#                 updated_token_data=UserMappingUseCase.refresh_user_key(user_profile.doubt_solving_uuid,api_key)
#                 if updated_token_data is not None:
#                     UserProfileRepository.update_doubt_solving_token(user_id,updated_token_data.get('user_id'),True,updated_token_data.get('user_key'),updated_token_data.get('expiration_time'))
#                     return updated_token_data
#                 else:
#                     return None
#         elif not user_profile.doubt_solving_mapping_created:
#             token_data=UserMappingUseCase.register_user(api_key)
#             if token_data is not None:
#                 UserProfileRepository.update_doubt_solving_token(user_id,token_data.get('user_id'),True,token_data.get('user_key'),token_data.get('expiration_time'))
#                 return token_data
#             else:
#                 return None
            
            
    