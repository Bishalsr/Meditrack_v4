from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import CustomUser, PasswordResetRequest


def _validate_password_or_redirect(password, *, request):
    try:
        validate_password(password)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return False
    return True

# Landing page for all users
def index(request):
    return render(request, "landing_page.html")  # project-level template


# Signup page
def signup_view(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        phone = (request.POST.get("phone") or "").strip()
        address = (request.POST.get("address") or "").strip()
        age_raw = (request.POST.get("age") or "").strip()
        gender = (request.POST.get("gender") or "").strip().upper()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password") or request.POST.get("password2")

        if not all([first_name, last_name, email, password, confirm_password]):
            messages.error(request, "All fields are required")
            return redirect("accounts:signup")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("accounts:signup")

        if not _validate_password_or_redirect(password, request=request):
            return redirect("accounts:signup")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("accounts:signup")

        age = None
        if age_raw:
            try:
                age = int(age_raw)
                if age <= 0:
                    raise ValueError
            except ValueError:
                messages.error(request, "Please enter a valid age")
                return redirect("accounts:signup")

        if gender and gender not in {"M", "F", "O"}:
            messages.error(request, "Please choose a valid gender")
            return redirect("accounts:signup")

        
        CustomUser.objects.create_user(
            email=email,
            password=password,
            is_authorized=True,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address,
            age=age,
            gender=gender,
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
        email = (request.POST.get("email") or "").strip().lower()
        if not email:
            messages.error(request, "Email is required")
            return redirect("accounts:forgot_password")

        user = CustomUser.objects.filter(email=email).first()
        if user:
            PasswordResetRequest.objects.filter(user=user).delete()
            reset_request = PasswordResetRequest.objects.create(user=user)
            reset_request.send_reset_email()

        messages.success(request, "Password reset link sent to your email")
        return redirect("accounts:login")

    return render(request, "forgot_password.html")


# RESET PASSWORD
def reset_password_view(request, token):
    reset_request = PasswordResetRequest.objects.filter(token=token).first()

    if not reset_request or not reset_request.is_valid():
        messages.error(request, "Invalid or expired reset link")
        return redirect("accounts:login")

    if request.method == "POST":
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if not new_password or not confirm_password:
            messages.error(request, "Both password fields are required")
            return redirect(request.path)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect(request.path)

        if not _validate_password_or_redirect(new_password, request=request):
            return redirect(request.path)

        user = reset_request.user
        user.set_password(new_password)
        user.save()

        reset_request.delete()  # single-use token

        messages.success(request, "Password reset successful")
        return redirect("accounts:login")

    return render(request, "reset_password.html", {"token": token})
