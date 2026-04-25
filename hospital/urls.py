from django.urls import path
from . import views

app_name = "hospital"

urlpatterns = [
    # Landing page (redirects based on user role)
    path("", views.landing_page, name="landing_page"),

    # Dashboards
    path("home/", views.home, name="home"),  # Admin / staff
    path("patient-dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("doctor-dashboard/", views.doctor_dashboard, name="doctor_dashboard"),
    path("doctor/patients/<int:patient_id>/records/", views.doctor_patient_records, name="doctor_patient_records"),
    path("receptionist-dashboard/", views.receptionist_dashboard, name="receptionist_dashboard"),
    path("doctors/export/pdf/", views.download_doctors_pdf, name="download_doctors_pdf"),
    path("user-role-assignment/", views.user_role_assignment, name="user_role_assignment"),

    # Lists
    path("patients/", views.patient_list, name="patient_list"),
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("appointments/", views.appointment_list, name="appointment_list"),
    path("medical-records/", views.medical_record_list, name="medical_record_list"),

    # Management
    path("patients/add/", views.add_patient, name="add_patient"),
    path("patients/edit/<int:pk>/", views.edit_patient, name="edit_patient"),
    path("patients/delete/<int:pk>/", views.delete_patient, name="delete_patient"),
    path("doctors/add/", views.add_doctor, name="add_doctor"),
    path("doctors/edit/<int:pk>/", views.edit_doctor, name="edit_doctor"),
    path("doctors/delete/<int:pk>/", views.delete_doctor, name="delete_doctor"),
    path("appointments/add/", views.add_appointment, name="add_appointment"),
    path("appointments/edit/<int:pk>/", views.edit_appointment, name="edit_appointment"),
    path("appointments/delete/<int:pk>/", views.delete_appointment, name="delete_appointment"),
    path("medical-records/add/", views.add_medical_record, name="add_medical_record"),
    path("medical-records/edit/<int:pk>/", views.edit_medical_record, name="edit_medical_record"),
    path("medical-records/delete/<int:pk>/", views.delete_medical_record, name="delete_medical_record"),

    # Patient files
    path("upload-file/<int:patient_id>/", views.upload_patient_file, name="upload_patient_file"),
    path("patient-files/", views.patient_files, name="patient_files"),
    path("patient-files/download/<int:file_id>/", views.download_patient_file, name="download_patient_file"),

    # Feedback
    path("feedback/submit/", views.feedback_submit, name="feedback_submit"),
]
