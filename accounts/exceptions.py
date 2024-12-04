from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.http import JsonResponse


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    redirect_url = "/accounts/login/"

    request = context["request"]

    if isinstance(exc, PermissionDenied):

        if "text/html" in request.META.get("HTTP_ACCEPT", ""):
            return redirect(redirect_url)
        else:
            return JsonResponse(
                {
                    "error": str(exc.detail.get("message", "Permission denied")),
                    "redirect_to": redirect_url,
                },
                status=403,
            )

    return response
