import firebase_admin
from django.conf import settings
from firebase_admin import credentials

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": settings.FIREBASE_ACCOUNT_TYPE,
        "project_id": settings.FIREBASE_PROJECT_ID,
        "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
        "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
        "client_email": settings.FIREBASE_CLIENT_EMAIL,
        "client_id": settings.FIREBASE_CLIENT_ID,
        "auth_uri": settings.FIREBASE_AUTH_URI,
        "token_uri": settings.FIREBASE_TOKEN_URI,
        "auth_provider_x509_cert_url": settings.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
        "client_x509_cert_url": settings.FIREBASE_CLIENT_X509_CERT_URL,
        "universe_domain": settings.FIREBASE_UNIVERSE_DOMAIN
        })
    firebase_admin.initialize_app(cred)
