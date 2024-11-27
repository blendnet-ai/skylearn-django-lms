from rest_framework import permissions


class UserPracticeHistoryPermission(permissions.BasePermission):
   
    def has_permission(self, request, view):
        req_user_id = view.kwargs.get('user_id')
        
        if not req_user_id:
            return True
        
        user = request.user
        
        if not user or not user.id:
            return False

        if user.is_superuser or user.is_staff:
            return True

        return False