import typing

# from InstituteConfiguration.models import Institute
# from InstituteConfiguration.repositories import QuestionListRepository

from .models import Form, UserProfile
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
ONBOARDING_FORM_NAME = 'onboarding'

logger = logging.getLogger(__name__)

class FormRepository:

    @staticmethod
    def fetch_form(form_name):
        form = Form.objects.get(form_name=form_name).form_data
        return form


class UserProfileRepository:

    @staticmethod
    def is_partner_admin_user(user_id):
        try:
            user_data =  UserProfile.objects.get(user_id=user_id).user_data
            if user_data is not None:
                return user_data.get('isPartnerAdmin', False)
        except UserProfile.DoesNotExist:
            logger.error(f"User profile does not exist and Partner admin check failed. User id: {user_id}.")
            return False

    # @staticmethod
    # def has_lab(user_id):
    #     institute_id = UserProfileRepository.get(user_id=user_id).institute_id
    #     has_lab = institute_id and QuestionListRepository.exists(institute_id)

    #     return has_lab

    @staticmethod
    def create_user_profile(*,user_id:str)->typing.Tuple[UserProfile,bool]:
        user = User.objects.get(id=user_id)
        return UserProfile.objects.get_or_create(user_id=user)

    def fetch_value_from_form(field_name, form_data):
        for section in form_data['sections']:
            for field in section['fields']:
                if field['name'] == field_name:
                    return field['value']
        return None

    @staticmethod
    def save_user_data(user_id, form_name, user_data):
        form = Form.objects.get(form_name=form_name)
        user = User.objects.get(id=user_id)

        user_profile,_ = UserProfile.objects.get_or_create(user_id=user)
        user_profile.user_data = user_data
        email = UserProfileRepository.fetch_value_from_form('email', user_data)
        name = UserProfileRepository.fetch_value_from_form('fullName', user_data)
        phone = UserProfileRepository.fetch_value_from_form('phone', user_data)
        user_profile.phone = phone
        user_profile.email = email
        user_profile.name = name
        user_profile.form_name = form
        if form_name == ONBOARDING_FORM_NAME:
            user_profile.onboarding_complete = True
        user_profile.save()

    @staticmethod
    def set_onboarding_complete(user_id: str):
        user,_ = User.objects.get_or_create(id=user_id)
        user_profile = UserProfile.objects.get(user_id=user)
        user_profile.onboarding_complete = True
        user_profile.save()

    @staticmethod
    def fetch_user_data(user_id):
        user = User.objects.get(id=user_id)
        saved_data = UserProfile.objects.filter(user_id=user).values('user_data')
        entire_data = UserProfile.objects.filter(user_id=user).values()
        onboarding_status = UserProfile.objects.filter(user_id=user, onboarding_complete=True).exists()
        return {"onboarding_status": onboarding_status, "data": saved_data, "entire_data": entire_data}
    
    def get_user_fullname(user_id):
        user = User.objects.get(id=user_id)
        name = UserProfile.objects.filter(user_id=user).values_list('name', flat=True).first() or ''
        return name

    # @staticmethod
    # def set_institute(user_id: str, institute: Institute):
    #     user_profile = UserProfile.objects.get(user_id=user_id)
    #     user_profile.institute = institute
    #     user_profile.save()

    @staticmethod
    def set_phone(user_id, phone):
        user_profile = UserProfile.objects.get(user_id=user_id)
        user_profile.phone = phone
        user_profile.save()

    @staticmethod
    def set_name(user_id, name):
        user_profile = UserProfile.objects.get(user_id=user_id)
        user_profile.name = name
        user_profile.save()

    @staticmethod
    def set_institute_roll_number(user_id, institute_roll_number):
        user_profile = UserProfile.objects.get(user_id=user_id)
        user_profile.institute_roll_number = institute_roll_number
        user_profile.save()
    
    @staticmethod
    def get_all_profiles_for_user_ids(user_ids):
        return UserProfile.objects.filter(user_id__in=user_ids)

    @staticmethod
    def get(user_id: str):
        try:
            return UserProfile.objects.get(
                user_id__id=user_id,
            )
        except UserProfile.DoesNotExist:
            return None
        
    @staticmethod
    def get_users_by_institute(institute):
        return UserProfile.objects.filter(institute=institute)
    
    @staticmethod
    def get_all_profiles():
        return UserProfile.objects.all()
    
    @staticmethod
    def update_doubt_solving_token(user_id, doubt_solving_uuid,doubt_solving_mapping_created,doubt_solving_token,token_expiration_time):
        user_profile=UserProfileRepository.get(user_id=user_id)
        user_profile.doubt_solving_mapping_created=doubt_solving_mapping_created
        user_profile.doubt_solving_token=doubt_solving_token
        user_profile.token_expiration_time=token_expiration_time
        user_profile.doubt_solving_uuid=doubt_solving_uuid
        user_profile.save()
        
