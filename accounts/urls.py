from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Landing / homepage
    path("", views.index, name="index"),

    # Signup
    path("signup/", views.signup_view, name="signup"),

    # Login
    path("login/", views.login_view, name="login"),

    # Logout
    path("logout/", views.logout_view, name="logout"),

    # Forgot / Reset Password
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/<str:token>/", views.reset_password_view, name="reset_password"),
]
