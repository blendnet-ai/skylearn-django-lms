from django.urls import path

from custom_auth.views import ActivityDataView, UserProfileApiView, UserListApiView, FormCRUD, FetchUserData, SignUpView, get_onboarding_status,determine_onboarding_step,send_otp,verify_otp,fetch_filled_data

urlpatterns = [
    path('profile', UserProfileApiView.as_view(), name='get_user_data'),
    path('users', UserListApiView.as_view(), name='get_users'),
    path('form', FormCRUD.as_view(), name='form_crud'),
    path('user-data', FetchUserData.as_view(), name='fetch_user_data'),
    path('activity-data', ActivityDataView.as_view(), name='activity_data'),
    path('sign-up', SignUpView.as_view(), name='sign_up'),
    path('onboarding/status', get_onboarding_status, name='get_onboarding_status'),
    path('onboarding/step', determine_onboarding_step, name='determine_onboarding_step'),
    path('onboarding/send-otp', send_otp, name='send_otp'),
    path('onboarding/verify-otp', verify_otp, name='verify_otp'),
    path('onboarding/fetch-data', fetch_filled_data, name='fetch_filled_data'),
    # path('get-doubt-solving-token',DoubtSolvingTokenView.as_view(), name='get_doubt_solving_token'),
    # path("onboarding/", OnBoardingView, name="onboarding")
]