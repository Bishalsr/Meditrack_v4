from django.core.management.base import BaseCommand
from django.db import transaction

from hospital.models import Doctor, MedicalRecord, Patient


class Command(BaseCommand):
    help = "Seed demo doctors, patients, and medical records."

    def handle(self, *args, **options):
        doctors_data = [
            {
                "first_name": "Anita",
                "last_name": "Shrestha",
                "specialization": "Cardiologist",
                "phone": "5550001001",
                "email": "anita.shrestha@meditrack.test",
                "room_number": "C101",
            },
            {
                "first_name": "Bikash",
                "last_name": "Thapa",
                "specialization": "Dermatologist",
                "phone": "5550001002",
                "email": "bikash.thapa@meditrack.test",
                "room_number": "D204",
            },
            {
                "first_name": "Chandra",
                "last_name": "Rana",
                "specialization": "Neurologist",
                "phone": "5550001003",
                "email": "chandra.rana@meditrack.test",
                "room_number": "N310",
            },
            {
                "first_name": "Dipa",
                "last_name": "Gurung",
                "specialization": "Pediatrician",
                "phone": "5550001004",
                "email": "dipa.gurung@meditrack.test",
                "room_number": "P120",
            },
            {
                "first_name": "Eshan",
                "last_name": "Karki",
                "specialization": "General",
                "phone": "5550001005",
                "email": "eshan.karki@meditrack.test",
                "room_number": "G001",
            },
        ]

        patients_data = [
            {
                "first_name": "Aarav",
                "last_name": "Basnet",
                "age": 29,
                "gender": "M",
                "phone": "5550002001",
                "email": "aarav.basnet@meditrack.test",
                "address": "Kumaripati, Lalitpur",
            },
            {
                "first_name": "Bina",
                "last_name": "Poudel",
                "age": 34,
                "gender": "F",
                "phone": "5550002002",
                "email": "bina.poudel@meditrack.test",
                "address": "New Road, Kathmandu",
            },
            {
                "first_name": "Chhaya",
                "last_name": "Roka",
                "age": 41,
                "gender": "F",
                "phone": "5550002003",
                "email": "chhaya.roka@meditrack.test",
                "address": "Biratnagar, Morang",
            },
            {
                "first_name": "Dipak",
                "last_name": "K.C.",
                "age": 52,
                "gender": "M",
                "phone": "5550002004",
                "email": "dipak.kc@meditrack.test",
                "address": "Pokhara, Kaski",
            },
            {
                "first_name": "Elina",
                "last_name": "Pandey",
                "age": 24,
                "gender": "F",
                "phone": "5550002005",
                "email": "elina.pandey@meditrack.test",
                "address": "Butwal, Rupandehi",
            },
            {
                "first_name": "Farhan",
                "last_name": "Khan",
                "age": 38,
                "gender": "M",
                "phone": "5550002006",
                "email": "farhan.khan@meditrack.test",
                "address": "Birgunj, Parsa",
            },
            {
                "first_name": "Gita",
                "last_name": "Maharjan",
                "age": 46,
                "gender": "F",
                "phone": "5550002007",
                "email": "gita.maharjan@meditrack.test",
                "address": "Bhaktapur Durbar, Bhaktapur",
            },
            {
                "first_name": "Hari",
                "last_name": "Lama",
                "age": 31,
                "gender": "M",
                "phone": "5550002008",
                "email": "hari.lama@meditrack.test",
                "address": "Dhulikhel, Kavre",
            },
            {
                "first_name": "Ishita",
                "last_name": "Shah",
                "age": 27,
                "gender": "F",
                "phone": "5550002009",
                "email": "ishita.shah@meditrack.test",
                "address": "Janakpur, Dhanusha",
            },
            {
                "first_name": "Jivan",
                "last_name": "Bista",
                "age": 58,
                "gender": "M",
                "phone": "5550002010",
                "email": "jivan.bista@meditrack.test",
                "address": "Dhangadhi, Kailali",
            },
        ]

        diagnoses = [
            "Hypertension",
            "Type 2 Diabetes",
            "Migraine",
            "Eczema",
            "Asthma",
            "Pneumonia",
            "Gastritis",
            "Osteoarthritis",
            "Anxiety Disorder",
            "Seasonal Allergies",
        ]

        tests = [
            "CBC, Lipid Panel",
            "HbA1c, Fasting Glucose",
            "MRI Brain",
            "Skin Patch Test",
            "Spirometry",
            "Chest X-Ray",
            "Upper GI Endoscopy",
            "X-Ray Knee",
            "PHQ-9, GAD-7",
            "IgE Panel",
        ]

        with transaction.atomic():
            doctors = []
            for data in doctors_data:
                doctor, _ = Doctor.objects.get_or_create(email=data["email"], defaults=data)
                doctors.append(doctor)

            for index, data in enumerate(patients_data):
                patient, _ = Patient.objects.get_or_create(email=data["email"], defaults=data)
                diagnosis = diagnoses[index % len(diagnoses)]
                test = tests[index % len(tests)]
                prescription = f"Standard care plan for {diagnosis}."

                if not MedicalRecord.objects.filter(patient=patient, diagnosis=diagnosis).exists():
                    MedicalRecord.objects.create(
                        patient=patient,
                        doctor=doctors[index % len(doctors)],
                        diagnosis=diagnosis,
                        prescriptions=prescription,
                        tests=test,
                    )

        self.stdout.write(self.style.SUCCESS("Seeded 5 doctors, 10 patients, and medical records."))
