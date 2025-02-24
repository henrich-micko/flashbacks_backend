from rest_framework.authtoken import views as rest_framework_views
from rest_framework import routers
from django.urls import path
from user import views

router = routers.DefaultRouter()
router.register(r"auth_user", views.AuthUserViewSet, basename="auth_user")
router.register(r"users", views.UserViewSet, basename="user")

urlpatterns = [
    path("auth/", rest_framework_views.obtain_auth_token),
    path("auth/google/", views.google_auth, name="google_auth")
] + router.urls
