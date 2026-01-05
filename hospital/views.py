from django.shortcuts import render, redirect
from .models import Patient, Doctor, Appointment
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Feedback  


@login_required
def home(request):
    user = request.user

    if user.is_superuser:
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_appointments = Appointment.objects.count()
    elif user.is_staff:
        doctor = Doctor.objects.filter(user=user).first()
        total_patients = Appointment.objects.filter(doctor=doctor).values('patient').distinct().count()
        total_doctors = 1
        total_appointments = Appointment.objects.filter(doctor=doctor).count()
    else:
        return redirect('patient_dashboard')
    
    recent_appointments = Appointment.objects.order_by('-appointment_date')[:5]

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'hospital/home.html', context)



@login_required
def patient_list(request):
    user = request.user
    if user.is_superuser:
        patients = Patient.objects.all()
    elif user.is_staff:
        doctor = Doctor.objects.filter(user=user).first()
        appointments = Appointment.objects.filter(doctor=doctor)
        patient_ids = appointments.values_list('patient', flat=True)
        patients = Patient.objects.filter(id__in=patient_ids)
    else:
        return redirect('patient_dashboard')

    return render(request, 'hospital/patient_list.html', {'patients': patients})

@login_required
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'hospital/doctor_list.html', {'doctors': doctors})


@login_required
def appointment_list(request):
    user = request.user
    
    if user.is_superuser:
        appointments = Appointment.objects.all()
   
    elif user.is_staff:
        doctor = Doctor.objects.filter(user=user).first()
        appointments = Appointment.objects.filter(doctor=doctor)
    else:
       
        return redirect('patient_dashboard')

    return render(request, 'hospital/appointment_list.html', {'appointments': appointments})





def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('home')  
            else:
                return redirect('patient_dashboard') 
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'hospital/login.html')


# @login_required
# def patient_dashboard(request):
#     try:
#         patient = Patient.objects.get(user=request.user)
#         appointments = Appointment.objects.filter(patient=patient)
#         records = MedicalRecord.objects.filter(patient=patient)
#     except Patient.DoesNotExist:
#         patient = None
#         appointments = []
#         records = []

#     return render(request, 'hospital/patient_dashboard.html', {
#         'patient': patient,
#         'appointments': appointments,
#         'records': records
#     })
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

    return render(request, 'hospital/patient_dashboard.html', context)

def landing_page(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('home')  # Staff dashboard
        else:
            return redirect('patient_dashboard')  # Patient dashboard

    context = {
        'hospital_name': 'MediTrack',
        'hospital_info': 'Welcome to MediTrack. We provide quality services.',
        'services': ['General Consultation', 'Pediatrics', 'Cardiology', 'Dermatology', 'Neurology'],
    }
    return render(request, 'hospital/landing_page.html', context)

@login_required
def doctor_dashboard(request):
    if request.user.is_staff and not request.user.is_superuser:
        try:
            doctor = Doctor.objects.get(user=request.user)
            appointments = Appointment.objects.filter(doctor=doctor)
        except Doctor.DoesNotExist:
            appointments = []
    else:
        
        appointments = Appointment.objects.all()

    return render(request, 'hospital/doctor_dashboard.html', {'appointments': appointments})

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

    return redirect('landing_page')


@login_required
def upload_patient_file(request, patient_id):
    if not request.user.is_staff:
        return redirect('home')

    patient = Patient.objects.get(id=patient_id)
    doctor = Doctor.objects.get(user=request.user)

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
        return redirect('doctor_dashboard')

    return render(request, 'hospital/upload_file.html', {'patient': patient})

@login_required
def patient_files(request):
    patient = Patient.objects.get(user=request.user)
    files = PatientFile.objects.filter(patient=patient)
    return render(request, 'hospital/patient_files.html', {'files': files})
