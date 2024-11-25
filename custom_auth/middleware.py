from django.shortcuts import redirect
from django.urls import reverse
from .repositories import UserProfileRepository
from django.utils.deprecation import MiddlewareMixin

class OnboardingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated and request.user.is_student:
                user_profile = UserProfileRepository.get(request.user.id)
                if not user_profile.onboarding_complete:
                    # Check if the current path is not the onboarding path
                    if request.path_info != reverse('onboarding'):
                        return redirect('onboarding')
        return None  
