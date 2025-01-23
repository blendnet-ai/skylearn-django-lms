from django.contrib.auth import get_user_model


def generate_password():
    return get_user_model().objects.make_random_password()
