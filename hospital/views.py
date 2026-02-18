import os

from django.http import FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count

from .models import (
    Appointment,
    Doctor,
    DoctorPrescriptionNote,
    Feedback,
    MedicalRecord,
    Patient,
    PatientFile,
    Receptionist,
)
from accounts.models import CustomUser  # for receptionist to manage users
from medi_rag.models import ChatMessage


def _can_manage_registry(user):
    return user.is_superuser or hasattr(user, "receptionist")


def _can_assign_user_roles(user):
    return user.is_superuser or hasattr(user, "receptionist")


def _name_parts_from_email(email, fallback_last_name):
    local = (email or "").split("@")[0].strip()
    cleaned = local.replace(".", " ").replace("_", " ").replace("-", " ")
    parts = [part for part in cleaned.split() if part]
    first_name = parts[0].title() if parts else "User"
    last_name = parts[1].title() if len(parts) > 1 else fallback_last_name
    return first_name, last_name


def _generate_unique_phone(model_cls, prefix, user_id):
    base = f"{prefix}{user_id}"
    candidate = base[:15]
    counter = 1
    while model_cls.objects.filter(phone=candidate).exists():
        suffix = str(counter)
        candidate = f"{base[:max(1, 15 - len(suffix))]}{suffix}"
        counter += 1
    return candidate


def _set_staff_flag_for_role(user, role):
    if user.is_superuser:
        return
    should_be_staff = role in {"doctor", "receptionist"}
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        user.save(update_fields=["is_staff"])


def _detach_existing_role_profiles(user):
    Patient.objects.filter(user=user).update(user=None)
    Doctor.objects.filter(user=user).update(user=None)
    Receptionist.objects.filter(user=user).update(user=None)


def _assign_role_to_user(user, role):
    with transaction.atomic():
        _detach_existing_role_profiles(user)

        if role == "unassigned":
            _set_staff_flag_for_role(user, role)
            return "Unassigned"

        if role == "patient":
            patient = Patient.objects.filter(email__iexact=user.email).first()
            if patient and patient.user and patient.user_id != user.id:
                raise ValueError("This patient profile is already linked to another user.")

            if not patient:
                first_name, last_name = _name_parts_from_email(user.email, "Patient")
                patient = Patient.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    age=0,
                    gender="O",
                    phone=None,
                    email=user.email,
                    address="To be updated",
                )
            else:
                patient.user = user
                patient.save(update_fields=["user"])

            _set_staff_flag_for_role(user, role)
            return "Patient"

        if role == "doctor":
            doctor = Doctor.objects.filter(email__iexact=user.email).first()
            if doctor and doctor.user and doctor.user_id != user.id:
                raise ValueError("This doctor profile is already linked to another user.")

            if not doctor:
                first_name, last_name = _name_parts_from_email(user.email, "Doctor")
                doctor = Doctor.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    specialization="General",
                    phone=_generate_unique_phone(Doctor, "DOC", user.id),
                    email=user.email,
                )
            else:
                doctor.user = user
                doctor.save(update_fields=["user"])

            _set_staff_flag_for_role(user, role)
            return "Doctor"

        if role == "receptionist":
            receptionist = Receptionist.objects.filter(email__iexact=user.email).first()
            if receptionist and receptionist.user and receptionist.user_id != user.id:
                raise ValueError("This receptionist profile is already linked to another user.")

            if not receptionist:
                first_name, last_name = _name_parts_from_email(user.email, "Receptionist")
                receptionist = Receptionist.objects.create(
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                    phone=_generate_unique_phone(Receptionist, "RCP", user.id),
                    email=user.email,
                )
            else:
                receptionist.user = user
                receptionist.save(update_fields=["user"])

            _set_staff_flag_for_role(user, role)
            return "Receptionist"

        raise ValueError("Invalid role selected.")


def _redirect_for_logged_in_role(user):
    if hasattr(user, "receptionist"):
        return "hospital:receptionist_dashboard"
    if hasattr(user, "doctor"):
        return "hospital:doctor_dashboard"
    if hasattr(user, "patient"):
        return "hospital:patient_dashboard"
    if user.is_superuser:
        return "hospital:home"
    return "hospital:landing_page"


ALLOWED_MEDICAL_FILE_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
    ".dcm",
}


def _validate_medical_files(uploaded_files):
    invalid_names = []
    for uploaded_file in uploaded_files:
        _, extension = os.path.splitext(uploaded_file.name.lower())
        if extension not in ALLOWED_MEDICAL_FILE_EXTENSIONS:
            invalid_names.append(uploaded_file.name)
    return invalid_names


def _save_medical_files(*, patient, doctor, medical_record, uploaded_files, base_title):
    total_files = len(uploaded_files)
    for index, uploaded_file in enumerate(uploaded_files, start=1):
        if base_title:
            title = base_title if total_files == 1 else f"{base_title} ({index})"
        else:
            title = uploaded_file.name

        PatientFile.objects.create(
            patient=patient,
            doctor=doctor,
            medical_record=medical_record,
            title=title[:200],
            file=uploaded_file,
        )


def landing_page(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'receptionist'):
            return redirect('hospital:receptionist_dashboard')
        elif hasattr(request.user, 'doctor'):
            return redirect('hospital:doctor_dashboard')
        elif hasattr(request.user, 'patient'):
            return redirect('hospital:patient_dashboard')
        elif request.user.is_staff or request.user.is_superuser:
            return redirect('hospital:home')
    
    context = {
        'hospital_name': 'MediTrack Medical Center',
        'hospital_info': 'Providing state-of-the-art healthcare services with a focus on patient well-being and advanced medical coordination.',
        'services': [
            'General Consultation',
            'Cardiology',
            'Pediatrics',
            'Radiology',
            'Pathology',
            'Emergency Care'
        ]
    }
    return render(request, 'landing_page.html', context)


# Admin / staff home
@login_required
def home(request):
    user = request.user
    if user.is_superuser:
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_appointments = Appointment.objects.count()
        recent_appointments = Appointment.objects.order_by('-appointment_date')[:5]
    elif user.is_receptionist:
        return redirect('hospital:receptionist_dashboard')
    elif user.is_doctor or user.is_staff:
        doctor = Doctor.objects.filter(user=user).first()
        if doctor:
            total_patients = Appointment.objects.filter(doctor=doctor).values('patient').distinct().count()
            total_doctors = 1
            total_appointments = Appointment.objects.filter(doctor=doctor).count()
            recent_appointments = Appointment.objects.filter(doctor=doctor).order_by('-appointment_date')[:5]
        else:
            total_patients = 0
            total_doctors = 0
            total_appointments = 0
            recent_appointments = Appointment.objects.none()
    elif user.is_patient:
        return redirect('hospital:patient_dashboard')
    else:
        return redirect('hospital:landing_page')

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'home.html', context)


# Patient dashboard
@login_required
def patient_dashboard(request):
    try:
        patient = Patient.objects.get(user=request.user)
        appointments = Appointment.objects.filter(patient=patient)
        files = PatientFile.objects.filter(patient=patient).order_by('-uploaded_at')
    except Patient.DoesNotExist:
        patient = None
        appointments = []
        files = []

    context = {
        'patient': patient,
        'appointments': appointments,
        'files': files
    }

    return render(request, 'patient_dashboard.html', context)


# Doctor dashboard
@login_required
def doctor_dashboard(request):
    if request.user.is_superuser:
        doctor = None
        appointments = Appointment.objects.all()
        patients = Patient.objects.all()
    elif hasattr(request.user, "doctor"):
        try:
            doctor = Doctor.objects.get(user=request.user)
            appointments = Appointment.objects.filter(doctor=doctor)
            patients = Patient.objects.filter(appointment__doctor=doctor).distinct()
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect("hospital:landing_page")
    else:
        messages.error(request, "Access denied")
        return redirect(_redirect_for_logged_in_role(request.user))

    if request.method == "POST" and "rag_question" in request.POST:
        question = (request.POST.get("rag_question") or "").strip()
        if not question:
            messages.error(request, "Please enter a question for the medical assistant.")
            return redirect("hospital:doctor_dashboard")

        try:
            from medi_rag.rag import ask_rag

            answer = ask_rag(question)
        except Exception:
            answer = "I could not generate a response right now. Please try again shortly."
            messages.error(request, "Medical assistant is currently unavailable.")

        try:
            ChatMessage.objects.create(
                user=request.user,
                question=question,
                answer=answer,
            )
        except Exception:
            messages.error(request, "Unable to save chat history.")

        return redirect("hospital:doctor_dashboard")

    try:
        latest_chat_history = list(
            ChatMessage.objects.filter(user=request.user)
            .order_by("-created_at")[:8]
        )
        chat_history = reversed(latest_chat_history)
    except Exception:
        chat_history = []

    return render(
        request,
        'doctor_dashboard.html',
        {
            'appointments': appointments,
            'patients': patients,
            'doctor': doctor,
            'chat_history': chat_history,
        },
    )


@login_required
def doctor_patient_records(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.user.is_superuser:
        doctor = None
        can_add_note = False
        records = (
            MedicalRecord.objects.filter(patient=patient)
            .select_related("doctor")
            .prefetch_related("attachments")
            .order_by("-record_date")
        )
        appointments = Appointment.objects.filter(patient=patient).select_related("doctor").order_by("-appointment_date")
    elif hasattr(request.user, "doctor"):
        doctor = get_object_or_404(Doctor, user=request.user)
        is_assigned = Appointment.objects.filter(doctor=doctor, patient=patient).exists()
        if not is_assigned:
            messages.error(request, "You can only view records for patients assigned to you.")
            return redirect("hospital:doctor_dashboard")
        can_add_note = True

        if request.method == "POST":
            prescription = request.POST.get("new_prescription", "").strip()
            suggestion = request.POST.get("new_suggestion", "").strip()

            if not (prescription or suggestion):
                messages.error(request, "Please add a prescription or a suggestion.")
                return redirect("hospital:doctor_patient_records", patient_id=patient.pk)

            DoctorPrescriptionNote.objects.create(
                patient=patient,
                doctor=doctor,
                prescription=prescription,
                suggestion=suggestion,
            )
            messages.success(request, "New prescription/suggestion entry added successfully.")
            return redirect("hospital:doctor_patient_records", patient_id=patient.pk)

        records = (
            MedicalRecord.objects.filter(patient=patient)
            .select_related("doctor")
            .prefetch_related("attachments")
            .order_by("-record_date")
        )
        appointments = Appointment.objects.filter(patient=patient, doctor=doctor).order_by("-appointment_date")
    else:
        messages.error(request, "Access denied")
        return redirect(_redirect_for_logged_in_role(request.user))

    doctor_notes = (
        DoctorPrescriptionNote.objects.filter(patient=patient)
        .select_related("doctor")
        .order_by("-created_at")
    )

    context = {
        "patient": patient,
        "records": records,
        "appointments": appointments,
        "doctor": doctor,
        "doctor_notes": doctor_notes,
        "can_add_note": can_add_note,
    }
    return render(request, "doctor_patient_records.html", context)


# Receptionist dashboard
@login_required
def receptionist_dashboard(request):
    if not hasattr(request.user, 'receptionist'):
        messages.error(request, "Access denied")
        return redirect('hospital:landing_page')

    users = CustomUser.objects.all()
    patients = Patient.objects.all()
    doctors = Doctor.objects.all()
    recent_patients = Patient.objects.order_by('-date_registered')[:5]
    recent_records = MedicalRecord.objects.select_related("patient", "doctor").order_by("-record_date")[:5]

    context = {
        'users': users,
        'patients': patients,
        'doctors': doctors,
        'recent_patients': recent_patients,
        'recent_records': recent_records,
    }
    return render(request, 'receptionist_dashboard.html', context)


@login_required
def user_role_assignment(request):
    if not _can_assign_user_roles(request.user):
        messages.error(request, "Access denied")
        return redirect(_redirect_for_logged_in_role(request.user))

    is_admin = request.user.is_superuser
    allow_receptionist_role = is_admin
    allow_unassign = is_admin

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        selected_role = (request.POST.get("role") or "").strip().lower()

        allowed_roles = {"doctor", "patient"}
        if allow_receptionist_role:
            allowed_roles.add("receptionist")
        if allow_unassign:
            allowed_roles.add("unassigned")

        if selected_role not in allowed_roles:
            messages.error(request, "You are not allowed to assign that role.")
            return redirect("hospital:user_role_assignment")

        target_user = get_object_or_404(CustomUser, pk=user_id)
        if target_user.is_superuser:
            messages.error(request, "Superuser role assignment is managed directly in Django admin.")
            return redirect("hospital:user_role_assignment")
        if not is_admin and hasattr(target_user, "receptionist"):
            messages.error(request, "Receptionist accounts can only manage doctor and patient roles.")
            return redirect("hospital:user_role_assignment")

        try:
            assigned_role = _assign_role_to_user(target_user, selected_role)
        except (ValueError, IntegrityError) as exc:
            messages.error(request, str(exc))
            return redirect("hospital:user_role_assignment")

        messages.success(
            request,
            f"{target_user.email} is now assigned as {assigned_role}.",
        )
        return redirect("hospital:user_role_assignment")

    users = CustomUser.objects.order_by("-date_joined")
    if not is_admin:
        users = users.filter(is_superuser=False, receptionist__isnull=True)
    context = {
        "users": users,
        "allow_receptionist_role": allow_receptionist_role,
        "allow_unassign": allow_unassign,
    }
    return render(request, "user_role_assignment.html", context)


# Feedback submission
def feedback_submit(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        if name and email and message:
            Feedback.objects.create(name=name, email=email, message=message)
            messages.success(request, 'Thank you for your feedback!')
        else:
            messages.error(request, 'Please fill all the fields.')

    return redirect('hospital:landing_page')


# Patient file upload
@login_required
def upload_patient_file(request, patient_id):
    if not hasattr(request.user, "doctor"):
        messages.error(request, "Only doctors can upload patient files.")
        return redirect(_redirect_for_logged_in_role(request.user))

    patient = get_object_or_404(Patient, id=patient_id)
    doctor = get_object_or_404(Doctor, user=request.user)

    if request.method == 'POST':
        title = request.POST['title']
        file = request.FILES['file']

        PatientFile.objects.create(
            patient=patient,
            doctor=doctor,
            title=title,
            file=file
        )
        messages.success(request, "File uploaded successfully")
        return redirect('hospital:doctor_dashboard')

    return render(request, 'upload_file.html', {'patient': patient})


@login_required
def patient_files(request):
    patient = get_object_or_404(Patient, user=request.user)
    files = PatientFile.objects.filter(patient=patient)
    return render(request, 'patient_files.html', {'files': files})


@login_required
def download_patient_file(request, file_id):
    patient = get_object_or_404(Patient, user=request.user)
    patient_file = get_object_or_404(PatientFile, pk=file_id, patient=patient)
    filename = os.path.basename(patient_file.file.name)
    return FileResponse(
        patient_file.file.open("rb"),
        as_attachment=True,
        filename=filename,
    )


@login_required
def patient_list(request):
    user = request.user
    if user.is_superuser or user.is_staff or hasattr(user, "receptionist"):
        patients = Patient.objects.all()
    else:
        return redirect('hospital:patient_dashboard')
    
    return render(request, 'patient_list.html', {'patients': patients})

@login_required
def doctor_list(request):
    user = request.user
    if user.is_superuser or user.is_staff or hasattr(user, "receptionist"):
        doctors = Doctor.objects.all()
    else:
        return redirect('hospital:patient_dashboard')
    
    return render(request, 'doctor_list.html', {'doctors': doctors})


@login_required
def appointment_list(request):
    user = request.user

    if user.is_superuser or hasattr(user, "receptionist"):
        appointments = Appointment.objects.all()
    elif user.is_staff:
        try:
            doctor = Doctor.objects.get(user=user)
            appointments = Appointment.objects.filter(doctor=doctor)
        except Doctor.DoesNotExist:
            appointments = []
    else:
        try:
            patient = Patient.objects.get(user=user)
            appointments = Appointment.objects.filter(patient=patient)
        except Patient.DoesNotExist:
            appointments = []

    return render(request, 'appointment_list.html', {'appointments': appointments})

# RECEPTIONIST CRUD FOR PATIENTS
@login_required
def add_patient(request):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        
        if Patient.objects.filter(email=email).exists():
            messages.error(request, "Patient with this email already exists")
            return redirect('hospital:add_patient')

        Patient.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            age=age,
            gender=gender,
            address=address
        )
        messages.success(request, "Patient added successfully")
        return redirect('hospital:patient_list')
    
    return render(request, 'patient_form.html', {'action': 'Add'})

@login_required
def edit_patient(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    patient = Patient.objects.get(pk=pk)
    if request.method == 'POST':
        patient.first_name = request.POST.get('first_name')
        patient.last_name = request.POST.get('last_name')
        patient.phone = request.POST.get('phone')
        patient.age = request.POST.get('age')
        patient.gender = request.POST.get('gender')
        patient.address = request.POST.get('address')
        patient.save()
        messages.success(request, "Patient updated successfully")
        return redirect('hospital:patient_list')
    
    return render(request, 'patient_form.html', {'patient': patient, 'action': 'Edit'})

@login_required
def delete_patient(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    patient = Patient.objects.get(pk=pk)
    patient.delete()
    messages.success(request, "Patient deleted successfully")
    return redirect('hospital:patient_list')


@login_required
def add_doctor(request):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        specialization = request.POST.get('specialization', '').strip()
        room_number = request.POST.get('room_number', '').strip()

        required_fields = [first_name, last_name, email, phone, specialization]
        if not all(required_fields):
            messages.error(request, "Please fill all required fields.")
            return redirect('hospital:add_doctor')

        valid_specializations = {value for value, _ in Doctor.SPECIALIZATION_CHOICES}
        if specialization not in valid_specializations:
            messages.error(request, "Please choose a valid specialization.")
            return redirect('hospital:add_doctor')

        if Doctor.objects.filter(email=email).exists():
            messages.error(request, "Doctor with this email already exists")
            return redirect('hospital:add_doctor')
        if Doctor.objects.filter(phone=phone).exists():
            messages.error(request, "Doctor with this phone already exists")
            return redirect('hospital:add_doctor')

        try:
            Doctor.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                specialization=specialization,
                room_number=room_number or None
            )
        except IntegrityError:
            messages.error(request, "Unable to add doctor due to invalid or duplicate data.")
            return redirect('hospital:add_doctor')

        messages.success(request, "Doctor added successfully")
        return redirect('hospital:doctor_list')
    
    return render(request, 'doctor_form.html', {'action': 'Add', 'specializations': Doctor.SPECIALIZATION_CHOICES})

@login_required
def edit_doctor(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    doctor = Doctor.objects.get(pk=pk)
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        specialization = request.POST.get('specialization', '').strip()
        room_number = request.POST.get('room_number', '').strip()

        required_fields = [first_name, last_name, phone, specialization]
        if not all(required_fields):
            messages.error(request, "Please fill all required fields.")
            return redirect('hospital:edit_doctor', pk=doctor.pk)

        valid_specializations = {value for value, _ in Doctor.SPECIALIZATION_CHOICES}
        if specialization not in valid_specializations:
            messages.error(request, "Please choose a valid specialization.")
            return redirect('hospital:edit_doctor', pk=doctor.pk)

        if Doctor.objects.filter(phone=phone).exclude(pk=doctor.pk).exists():
            messages.error(request, "Doctor with this phone already exists")
            return redirect('hospital:edit_doctor', pk=doctor.pk)

        doctor.first_name = first_name
        doctor.last_name = last_name
        doctor.phone = phone
        doctor.specialization = specialization
        doctor.room_number = room_number or None
        try:
            doctor.save()
        except IntegrityError:
            messages.error(request, "Unable to update doctor due to invalid or duplicate data.")
            return redirect('hospital:edit_doctor', pk=doctor.pk)

        messages.success(request, "Doctor updated successfully")
        return redirect('hospital:doctor_list')
    
    return render(request, 'doctor_form.html', {'doctor': doctor, 'action': 'Edit', 'specializations': Doctor.SPECIALIZATION_CHOICES})

@login_required
def delete_doctor(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    doctor = Doctor.objects.get(pk=pk)
    doctor.delete()
    messages.success(request, "Doctor deleted successfully")
    return redirect('hospital:doctor_list')


# RECEPTIONIST CRUD FOR MEDICAL RECORDS
@login_required
def medical_record_list(request):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect("hospital:home")

    records = (
        MedicalRecord.objects.select_related("patient", "doctor")
        .annotate(attachment_count=Count("attachments"))
        .order_by("-record_date")
    )
    return render(request, "medical_record_list.html", {"records": records})


@login_required
def add_medical_record(request):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect("hospital:home")

    if request.method == "POST":
        patient_id = request.POST.get("patient")
        doctor_id = request.POST.get("doctor")
        diagnosis = request.POST.get("diagnosis", "").strip()
        prescriptions = request.POST.get("prescriptions", "").strip()
        tests = request.POST.get("tests", "").strip()
        file_title = request.POST.get("file_title", "").strip()
        uploaded_files = request.FILES.getlist("medical_files")

        if not (patient_id and diagnosis and prescriptions):
            messages.error(request, "Patient, diagnosis, and prescriptions are required.")
            return redirect("hospital:add_medical_record")

        invalid_files = _validate_medical_files(uploaded_files)
        if invalid_files:
            messages.error(
                request,
                "Unsupported file type. Upload PDF, JPG, JPEG, PNG, WEBP, BMP, TIF, TIFF, or DCM files only.",
            )
            return redirect("hospital:add_medical_record")

        patient = get_object_or_404(Patient, pk=patient_id)
        doctor = Doctor.objects.filter(pk=doctor_id).first() if doctor_id else None

        record = MedicalRecord.objects.create(
            patient=patient,
            doctor=doctor,
            diagnosis=diagnosis,
            prescriptions=prescriptions,
            tests=tests,
        )

        if uploaded_files:
            _save_medical_files(
                patient=patient,
                doctor=doctor,
                medical_record=record,
                uploaded_files=uploaded_files,
                base_title=file_title,
            )
            messages.success(
                request,
                f"Medical record added successfully with {len(uploaded_files)} file(s).",
            )
        else:
            messages.success(request, "Medical record added successfully")
        return redirect("hospital:medical_record_list")

    context = {
        "patients": Patient.objects.all(),
        "doctors": Doctor.objects.all(),
        "action": "Add",
        "existing_files": [],
    }
    return render(request, "medical_record_form.html", context)


@login_required
def edit_medical_record(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect("hospital:home")

    record = get_object_or_404(MedicalRecord, pk=pk)

    if request.method == "POST":
        patient_id = request.POST.get("patient")
        doctor_id = request.POST.get("doctor")
        diagnosis = request.POST.get("diagnosis", "").strip()
        prescriptions = request.POST.get("prescriptions", "").strip()
        tests = request.POST.get("tests", "").strip()
        file_title = request.POST.get("file_title", "").strip()
        uploaded_files = request.FILES.getlist("medical_files")

        if not (patient_id and diagnosis and prescriptions):
            messages.error(request, "Patient, diagnosis, and prescriptions are required.")
            return redirect("hospital:edit_medical_record", pk=record.pk)

        invalid_files = _validate_medical_files(uploaded_files)
        if invalid_files:
            messages.error(
                request,
                "Unsupported file type. Upload PDF, JPG, JPEG, PNG, WEBP, BMP, TIF, TIFF, or DCM files only.",
            )
            return redirect("hospital:edit_medical_record", pk=record.pk)

        record.patient = get_object_or_404(Patient, pk=patient_id)
        record.doctor = Doctor.objects.filter(pk=doctor_id).first() if doctor_id else None
        record.diagnosis = diagnosis
        record.prescriptions = prescriptions
        record.tests = tests
        record.save()
        record.attachments.update(patient=record.patient, doctor=record.doctor)

        if uploaded_files:
            _save_medical_files(
                patient=record.patient,
                doctor=record.doctor,
                medical_record=record,
                uploaded_files=uploaded_files,
                base_title=file_title,
            )
            messages.success(
                request,
                f"Medical record updated and {len(uploaded_files)} file(s) uploaded.",
            )
        else:
            messages.success(request, "Medical record updated successfully")
        return redirect("hospital:medical_record_list")

    context = {
        "record": record,
        "patients": Patient.objects.all(),
        "doctors": Doctor.objects.all(),
        "action": "Edit",
        "existing_files": record.attachments.order_by("-uploaded_at"),
    }
    return render(request, "medical_record_form.html", context)


@login_required
def delete_medical_record(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect("hospital:home")

    record = get_object_or_404(MedicalRecord, pk=pk)
    record.delete()
    messages.success(request, "Medical record deleted successfully")
    return redirect("hospital:medical_record_list")

# APPOINTMENT CRUD
@login_required
def add_appointment(request):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        date_str = request.POST.get('appointment_date')
        reason = request.POST.get('reason')
        status = request.POST.get('status', 'Pending')
        
        patient = Patient.objects.get(pk=patient_id)
        doctor = Doctor.objects.get(pk=doctor_id)
        
        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=date_str,
            reason=reason,
            status=status
        )
        messages.success(request, "Appointment recorded successfully")
        return redirect('hospital:appointment_list')
    
    patients = Patient.objects.all()
    doctors = Doctor.objects.all()
    context = {
        'patients': patients,
        'doctors': doctors,
        'action': 'Record',
        'status_choices': Appointment.STATUS_CHOICES
    }
    return render(request, 'appointment_form.html', context)

@login_required
def edit_appointment(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    appointment = Appointment.objects.get(pk=pk)
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        date_str = request.POST.get('appointment_date')
        reason = request.POST.get('reason')
        status = request.POST.get('status')
        
        appointment.patient = Patient.objects.get(pk=patient_id)
        appointment.doctor = Doctor.objects.get(pk=doctor_id)
        appointment.appointment_date = date_str
        appointment.reason = reason
        appointment.status = status
        appointment.save()
        messages.success(request, "Appointment updated successfully")
        return redirect('hospital:appointment_list')
    
    patients = Patient.objects.all()
    doctors = Doctor.objects.all()
    context = {
        'appointment': appointment,
        'patients': patients,
        'doctors': doctors,
        'action': 'Edit',
        'status_choices': Appointment.STATUS_CHOICES
    }
    return render(request, 'appointment_form.html', context)

@login_required
def delete_appointment(request, pk):
    if not _can_manage_registry(request.user):
        messages.error(request, "Permission denied")
        return redirect('hospital:home')
    
    appointment = Appointment.objects.get(pk=pk)
    appointment.delete()
    messages.success(request, "Appointment cancelled successfully")
    return redirect('hospital:appointment_list')
