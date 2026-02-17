# MediTrack - Patient Management System

MediTrack is a Django-based patient management system for clinics/hospitals.  
It supports role-based dashboards for **Admin**, **Receptionist**, **Doctor**, and **Patient**, with medical records, appointments, file sharing, and prescription/suggestion tracking.

## Features

- Custom email-based authentication (`CustomUser`)
- Role-based dashboards:
  - Admin dashboard
  - Receptionist dashboard
  - Doctor dashboard
  - Patient dashboard
- User role assignment workflow:
  - Admin can assign: `patient`, `doctor`, `receptionist`
  - Receptionist can assign: `patient`, `doctor`
- Patient management (add/edit/delete)
- Doctor management (add/edit/delete)
- Appointment management (add/edit/delete)
- Medical records management
- Doctor-only patient record view with:
  - disease/diagnosis history
  - prescriptions and tests
  - attached files
  - separate add-new prescription/suggestion entries (append-only)
- File upload and sharing:
  - Doctor uploads medical files for patient
  - Reception can attach files while adding/editing medical records
  - Patient can open and download own files
- Forgot/reset password flow
- Optional Google login via `django-allauth`
- Separate admin and app sessions (can stay logged in with different accounts)

## Tech Stack

- Python
- Django
- SQLite (default)
- django-allauth
- django-jazzmin
- Bootstrap (templates)

See `requirements.txt` for full dependency list.

## Project Structure

- `meditrack/` - project settings, URLs, middleware
- `accounts/` - custom auth, login/signup/logout, password reset
- `hospital/` - core domain models, views, urls, admin, migrations
- `templates/` - frontend templates
- `media/` - uploaded files

## Prerequisites

- Python 3.10+ recommended
- pip
- Virtual environment tool (`venv`)

## Setup (PowerShell)

1. Clone the repository and open project folder.

2. Create and activate virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create `.env` in project root (example):

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@localhost
```

5. Apply migrations:

```powershell
python manage.py migrate
```

6. Create superuser:

```powershell
python manage.py createsuperuser
```

7. Run development server:

```powershell
python manage.py runserver
```

Open:
- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Authentication & Role Flow

- New local signup users are authorized by default (via `accounts/signals.py`).
- Users initially can be unassigned to domain roles.
- Admin or receptionist assigns users in:
  - `User Roles` page (`/user-role-assignment/`)
- Role-based redirect on login:
  - receptionist -> receptionist dashboard
  - doctor -> doctor dashboard
  - patient -> patient dashboard
  - otherwise -> landing page

## Key Routes

- `GET /` - landing page with role-based redirect if authenticated
- `GET /auth/login/` - login
- `GET /auth/signup/` - signup
- `GET /admin/` - Django admin
- `GET /doctor-dashboard/` - doctor dashboard
- `GET /doctor/patients/<id>/records/` - doctor patient details + records
- `GET /patient-dashboard/` - patient dashboard
- `GET /patient-files/download/<file_id>/` - secure patient file download
- `GET /user-role-assignment/` - role assignment (admin/receptionist)

## Session Behavior (Important)

This project uses custom middleware `SplitSessionMiddleware` (`meditrack/middleware.py`) to separate:

- app session cookie: `app_sessionid`
- admin session cookie: `admin_sessionid`

This allows using different accounts in app and admin at the same time in one browser.

## File Upload Paths

- Doctor images: `media/doctor_images/`
- Patient files: `media/patient_files/`

## Validation / Health Check

Run:

```powershell
python manage.py check
```

## Notes for Production

- Set `DEBUG=False`
- Use a strong `SECRET_KEY` from environment
- Configure allowed hosts and CSRF trusted origins
- Use production database (e.g., PostgreSQL)
- Serve static/media via proper web server or storage service
- Configure secure cookies/HTTPS

---

If you want, I can also add:
- API documentation section
- screenshots section
- deployment steps (Render/Railway/EC2)
- contributor/developer workflow section
