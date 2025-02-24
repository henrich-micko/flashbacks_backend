from django.contrib.auth.base_user import BaseUserManager
from rest_framework.authtoken.models import Token


class UserManager(BaseUserManager):
    def create_user(self, username: str, email: str, password: str, **extra_fields):
        if not email or not username or not password:
            raise ValueError("email/username/password is not set.")
        
        email = self.normalize_email(email)

        user = self.model(username = username, email = email, **extra_fields)
        user.set_password(password)
        user.save()

        Token.objects.create(user = user)
        return user

    def create_superuser(self, username: str, email: str, password: str, **extra_fields):
        if not email or not username or not password:
            raise ValueError("email/username/password is not set.")
        
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is False:
            raise ValueError("Superuser must have is_staff set as True.")

        if extra_fields.get("is_superuser") is False:
            raise ValueError("Superuser must have is_superuser set as True.")

        return self.create_user(username, email, password, **extra_fields)