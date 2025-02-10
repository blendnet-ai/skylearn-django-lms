from datetime import datetime,timedelta
from email import message
from django.utils import timezone
import logging
import firebase_admin

# from InstituteConfiguration.repositories import InstituteRepository
from custom_auth.repositories import UserProfileRepository
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.services.sendgrid_service import SendgridService

from data_repo.repositories import ConfigMapRepository
from evaluation.management.register.utils import Utils
from evaluation.repositories import AssessmentAttemptRepository
from config.settings import TELEGRAM_BOT_NAME, TWO_Factor_SMS_API_KEY
from services.sms_service import SMS2FactorService

logger = logging.getLogger(__name__)
SMS2FactorService = SMS2FactorService(api_key=TWO_Factor_SMS_API_KEY)  # 2
from Feedback.usecases import FeedbackResponseUsecase
from django.conf import settings


class BetaUserlistUsecase:
    @staticmethod
    def mark_onboarding_complete_for_user_if_not(*, email: str, user_id: str):
        existing_profile = UserProfileRepository.fetch_user_data(user_id)
        if not existing_profile.get("onboarding_status"):
            UserProfileRepository.set_onboarding_complete(user_id)

    @staticmethod
    def mark_onboarding_complete_if_whitelisted_user(*, email: str, user_id: str):
        whitelisted_user_emails = ConfigMapRepository.get_config_by_tag(
            tag=ConfigMapRepository.WHITELISTED_USER_EMAILS
        )
        if email in whitelisted_user_emails:
            logger.info(
                f"Marking user email - {email},id={user_id} as on-boarding completed."
            )
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

        yesterday = today - timedelta(days=1)

        user_profile = UserProfileRepository.get(user_id=user_id)

        if not AssessmentAttemptRepository.does_attempts_exist_for_date(
            today
        ) and not AssessmentAttemptRepository.does_attempts_exist_for_date(yesterday):
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
            "longest_streak": longest_streak,
            "current_streak": current_streak,
            "activity_status": activity_status,
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


class OnBoardingUsecase:
    @staticmethod
    def get_onboaring_status(user):
        role = "no_role"
        if user.is_student:
            role = "student"
        elif user.is_lecturer:
            role = "lecturer"
        elif user.is_course_provider_admin:
            role = "course_provider_admin"

        if user.is_student:
            onboarding_status = UserProfileRepository.get_onboarding_status_details(
                user.id
            )
            user_name = user.get_full_name
            if settings.DEPLOYMENT_TYPE == "ECF":
                onboarding_status["onboarding_status"]=True
            onboarding_status["telegram_url"] = (
                f"https://t.me/{TELEGRAM_BOT_NAME}?start={onboarding_status['otp']}"
            )
            onboarding_status["role"] = role
            # Get all batch IDs for the student
            batch_ids = user.student.batches.all().values_list('id', flat=True)
            # Check if there are any pending forms for any batch
            has_pending_forms = False
            for batch_id in batch_ids:
                forms = FeedbackResponseUsecase.check_if_any_pending_mandatory_forms(
                    user.id, batch_id, datetime.now().date()
                )
                if forms:
                    has_pending_forms = True
                    break
            onboarding_status["pending_forms"] = has_pending_forms
            onboarding_status["user_name"] = user_name
            return onboarding_status
        elif user.is_lecturer:
            onboarding_status = UserProfileRepository.get_onboarding_status_details(
                user.id
            )
            onboarding_status["telegram_url"] = (
                f"https://t.me/{TELEGRAM_BOT_NAME}?start={onboarding_status['otp']}"
            )
            onboarding_status["role"] = role
            return onboarding_status
        else:
            return {
                "telegram_status": True,
                "mobile_verification_status": True,
                "onboarding_status": True,
                "onboarding_cv_status": True,
                "otp": "000000",
                "role": role,
            }
    @staticmethod
    def determine_onboarding_step(user_id):
        onboarding_details = UserProfileRepository.get_onboarding_status_details(
            user_id
        )
        if not onboarding_details["mobile_verification_status"]:
            return "mobile_verification"

        elif (
            onboarding_details["mobile_verification_status"] 
            and not onboarding_details["onboarding_status"]
            and settings.DEPLOYMENT_TYPE != "ECF"
        ):
            return "onboarding_form"

        elif (
            onboarding_details["mobile_verification_status"]
            and (onboarding_details["onboarding_status"] or settings.DEPLOYMENT_TYPE == "ECF")
            and not onboarding_details["telegram_status"]
        ):
            return "telegram_onboarding"
        
        elif (
            onboarding_details["mobile_verification_status"]
            and (onboarding_details["onboarding_status"] or settings.DEPLOYMENT_TYPE == "ECF")
            and onboarding_details["telegram_status"]
            and not onboarding_details["onboarding_cv_status"]
        ):
            return "cv_upload"

    def handle_otp_sending(user, phone_number):
        if UserProfileRepository.is_phone_taken(phone_number):
            return {
                "otp_sent": False,
                "status": False,
                "message": "Phone Number already taken",
            }

        if phone_number:
            status, message, code = SMS2FactorService.send_otp(phone_number)
            # status,message=True,"OTP Sent Successfully"
            if status:
                return {"otp_sent": True, "status": status, "message": message, "code":code}
            else:
                return {"otp_sent": False, "status": status, "message": message, "code":code}
        else:
            return {
                "otp_sent": False,
                "status": False,
                "message": "Please provide phone number",
            }

    def handle_otp_verification(user, code, entered_otp_value,phone_number):
        is_verified, message = SMS2FactorService.verify_otp(
            code, entered_otp_value
        )

        if is_verified:
            UserProfileRepository.set_mobile_verification_complete(user, phone_number)
            return {"otp_verified": is_verified, "message": message}
        else:
            return {"otp_verified": is_verified, "message": message}

    def add_cv_upload_link(user, link, linked_in_link, status):
        UserProfileRepository.set_cv_data(user, link, linked_in_link, status)
        return {"cv_link_added": True}
    
    def skip_telegram_onboarding(user):
        UserProfileRepository.skip_telegram_onboarding(user)
        return {"telegram_skipped":True,"message":"telegram onboarding skipped"}
    
    # def handle_fetching_filled_data( user):
    #     data = GDWrapperIntance.find_row_by_value('dummy', 'Serail Number', '212')
    #     if data is not None:
    #         UserProfileRepository.set_user_profile_user_data(user, data)
    #         UserProfileRepository.set_onboarding_complete(user.id)
    #         return {'onboarding_data_fetched':True,'data':data}
    #     else:
    #         return {'onboarding_data_fetched':False,'data':data}


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
