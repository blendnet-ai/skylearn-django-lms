from django.urls import path

from custom_auth.views import ActivityDataView, UserProfileApiView, UserListApiView, FormCRUD, FetchUserData, SignUpView,DoubtSolvingTokenView

urlpatterns = [
    path('profile', UserProfileApiView.as_view(), name='get_user_data'),
    path('users', UserListApiView.as_view(), name='get_users'),
    path('form', FormCRUD.as_view(), name='form_crud'),
    path('user-data', FetchUserData.as_view(), name='fetch_user_data'),
    path('activity-data', ActivityDataView.as_view(), name='activity_data'),
    path('sign-up', SignUpView.as_view(), name='sign_up'),
    path('get-doubt-solving-token',DoubtSolvingTokenView.as_view(), name='get_doubt_solving_token'),
]