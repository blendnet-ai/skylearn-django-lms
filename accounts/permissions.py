from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from accounts.authentication import FirebaseAuthentication


def firebase_drf_authentication(*permission_classes_args):
    """
    Decorator factory that creates a decorator with specified permission classes.
    Usage: @method_decorator(drf_authentication(IsLoggedIn, IsLecturer), name='dispatch')
    """

    def decorator(view_func):
        decorated_view = api_view(["GET"])(view_func)  # Add other methods as needed
        decorated_view = authentication_classes([FirebaseAuthentication])(
            decorated_view
        )
        decorated_view = permission_classes(permission_classes_args)(decorated_view)
        return decorated_view

    return decorator


class BasePermissionImplementation(BasePermission):
    """
    Base permission class with redirect capability.
    """

    message = "Access required"

    def has_permission(self, request, view):
        is_permitted = self.check_permission(request.user)
        if not is_permitted:
            raise PermissionDenied(detail={"message": self.message})

        return is_permitted

    def check_permission(self, user):
        """Override this method in subclasses"""
        raise NotImplementedError


class IsStudent(BasePermissionImplementation):
    """
    Permission check for student access with redirect capability.
    """

    message = "Student access required"

    def check_permission(self, user):
        return bool(user and user.is_active and (user.is_student or user.is_superuser))


class IsLecturer(BasePermissionImplementation):
    """
    Permission check for lecturer access with redirect capability.
    """

    message = "Lecturer access required"

    def check_permission(self, user):
        return bool(user and user.is_active and (user.is_lecturer or user.is_superuser))


class IsSuperuser(BasePermissionImplementation):
    """
    Permission check for superuser access with redirect capability.
    """

    message = "Superuser access required"

    def check_permission(self, user):
        return bool(user and user.is_active and user.is_superuser)


class IsLoggedIn(BasePermissionImplementation):
    """
    Permission check for authenticated users with redirect capability.
    """

    message = "Authentication required"

    def check_permission(self, user):
        return bool(user and user.is_authenticated)


class IsCourseProviderAdminOrLecturer(BasePermissionImplementation):
    """
    Permission check for course provider admin or lecturer access with redirect capability.
    """

    message = "Course provider admin or lecturer access required"

    def check_permission(self, user):
        return (
            user.is_active
            and (user.is_course_provider_admin or user.is_lecturer)
            or user.is_superuser
        )


class IsCourseProviderAdmin(BasePermissionImplementation):
    """
    Permission check for course provider admin access with redirect capability.
    """

    message = "Course provider admin access required"

    def check_permission(self, user):
        return user.is_active and user.is_course_provider_admin or user.is_superuser
