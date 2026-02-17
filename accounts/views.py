from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.conf import settings

from .models import CustomUser, PasswordResetRequest

# Landing page for all users
def index(request):
    return render(request, "landing_page.html")  # project-level template


# Signup page
def signup_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password") or request.POST.get("password2")

        if not email or not password or not confirm_password:
            messages.error(request, "All fields are required")
            return redirect("accounts:signup")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("accounts:signup")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect("accounts:signup")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("accounts:signup")

        # Keep local signup usable without separate approval workflow.
        CustomUser.objects.create_user(
            email=email,
            password=password,
            is_authorized=True,
        )

        messages.success(request, "Signup successful. Please login.")
        return redirect("accounts:login")

    return render(request, "signup.html")


# Login page
def login_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or request.POST.get("username") or "").strip().lower()
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid credentials")
            return redirect("accounts:login")

        if not user.is_authorized and not settings.DEBUG:
            messages.error(request, "Your account is not authorized yet")
            return redirect("accounts:login")
        if not user.is_authorized and settings.DEBUG:
            user.is_authorized = True
            user.save(update_fields=["is_authorized"])

        auth_login(request, user)
        messages.success(request, "Welcome to MediTrack")

        # Redirect based on role
        if hasattr(user, 'receptionist'):
            return redirect("hospital:receptionist_dashboard")
        elif hasattr(user, 'doctor'):
            return redirect("hospital:doctor_dashboard")
        elif hasattr(user, 'patient'):
            return redirect("hospital:patient_dashboard")
        elif user.is_staff or user.is_superuser:
            return redirect("hospital:home")
        else:
            messages.info(request, "Your account is active but no role is assigned yet.")
            return redirect("hospital:landing_page")

    return render(request, "login.html")


# Logout
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been logged out")
    return redirect("hospital:landing_page")


# Removed redundant views


# FORGOT PASSWORD
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = CustomUser.objects.filter(email=email).first()

        if not user:
            messages.error(request, "Email not found")
            return redirect("accounts:login")

        # Delete previous tokens
        PasswordResetRequest.objects.filter(user=user).delete()

        # Create new reset token
        reset_request = PasswordResetRequest.objects.create(user=user)
        reset_request.send_reset_email()

        messages.success(request, "Password reset link sent to your email")
        return redirect("accounts:login")

    return render(request, "login.html")


# RESET PASSWORD
def reset_password_view(request, token):
    reset_request = PasswordResetRequest.objects.filter(token=token).first()

    if not reset_request or not reset_request.is_valid():
        messages.error(request, "Invalid or expired reset link")
        return redirect("accounts:login")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect(request.path)

        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect(request.path)

        user = reset_request.user
        user.set_password(new_password)
        user.save()

        reset_request.delete()  # single-use token

        messages.success(request, "Password reset successful")
        return redirect("accounts:login")

    return render(request, "reset_password.html", {"token": token})
