from django.contrib import admin
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

admin.site.site_header = "MediTrack Admin"
admin.site.site_title = "MediTrack Admin Portal"
admin.site.index_title = "Welcome to MediTrack Admin"

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "user", "date_registered")
    search_fields = ("first_name", "last_name", "email", "phone", "user__email")
    list_filter = ("gender", "date_registered")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "specialization", "email", "phone", "user")
    search_fields = ("first_name", "last_name", "email", "phone", "specialization", "user__email")
    list_filter = ("specialization",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "appointment_date", "status")
    search_fields = (
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
    )
    list_filter = ("status", "appointment_date")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "record_date")
    search_fields = (
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
        "diagnosis",
    )
    list_filter = ("record_date",)


@admin.register(DoctorPrescriptionNote)
class DoctorPrescriptionNoteAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "created_at")
    search_fields = ("patient__first_name", "patient__last_name", "doctor__first_name", "doctor__last_name")
    list_filter = ("created_at",)


@admin.register(PatientFile)
class PatientFileAdmin(admin.ModelAdmin):
    list_display = ("title", "patient", "doctor", "medical_record", "uploaded_at")
    search_fields = ("title", "patient__first_name", "patient__last_name")
    list_filter = ("uploaded_at",)


@admin.register(Receptionist)
class ReceptionistAdmin(admin.ModelAdmin):
    # Superuser can assign a receptionist to an existing user from admin.
    list_display = ("first_name", "last_name", "email", "phone", "shift", "user")
    search_fields = ("first_name", "last_name", "email", "phone", "user__email")
    list_filter = ("shift", "date_joined")

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message', 'submitted_at')
    search_fields = ('name', 'email', 'message')
    list_filter = ('submitted_at',)
    list_per_page = 10
