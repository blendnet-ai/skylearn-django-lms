from django.conf import settings


def firebase_config(request):
    return {
        "FIREBASE_API_KEY": settings.FIREBASE_API_KEY,
        "FIREBASE_AUTH_DOMAIN": settings.FIREBASE_AUTH_DOMAIN,
        "FIREBASE_PROJECT_ID": settings.FIREBASE_PROJECT_ID,
        "FIREBASE_STORAGE_BUCKET": settings.FIREBASE_STORAGE_BUCKET,
        "FIREBASE_MESSAGING_SENDER_ID": settings.FIREBASE_MESSAGING_SENDER_ID,
        "FIREBASE_APP_ID": settings.FIREBASE_APP_ID,
        "FIREBASE_MEASUREMENT_ID": settings.FIREBASE_MEASUREMENT_ID,
    }
