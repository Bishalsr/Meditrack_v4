from django.test import SimpleTestCase

from .rag import NO_DOCTOR_FOUND, recommend_doctor


class DoctorRecommendationTests(SimpleTestCase):
    def test_exact_disease_match_returns_expected_doctor_first(self):
        recommendation = recommend_doctor("asthma")
        lines = recommendation.splitlines()
        self.assertEqual("Recommended doctors:", lines[0])
        self.assertIn("1. Dr. Sunita Rai (asthma)", lines[1])

    def test_multi_disease_query_returns_ranked_top_matches(self):
        recommendation = recommend_doctor("asthma, bronchitis, pneumonia")
        lines = recommendation.splitlines()
        self.assertIn("1. Dr. Sunita Rai (asthma)", lines[1])
        self.assertIn("2. Dr. Sita Tamang (bronchitis)", lines[2])
        self.assertIn("3. Dr. Sita Karki (pneumonia)", lines[3])

    def test_phrase_with_disease_still_matches(self):
        recommendation = recommend_doctor("Patient is suffering from chronic kidney disease")
        self.assertIn("Dr. Michael Lee", recommendation)

    def test_symptom_query_falls_back_to_specialization_directory(self):
        recommendation = recommend_doctor("chest pain and palpitations")
        self.assertIn("Dr. Anita Shrestha", recommendation)

    def test_unknown_query_returns_no_match_message(self):
        recommendation = recommend_doctor("broken spaceship syndrome")
        self.assertEqual(NO_DOCTOR_FOUND, recommendation)
