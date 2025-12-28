from django.dispatch import receiver
from django.contrib.auth.models import User


def save_google_profile(backend, user, response, *args, **kwargs):
    if backend.name == "google-oauth2":
        user.avatar = response.get("picture")
        user.save()