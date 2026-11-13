"""
MedBuddy Automated Verification Test Suite
Executes end-to-end verification across all 10 Grand Modules.
Run with: python -m unittest tests/test_verification_suite.py -v
"""

import unittest
import os
import sys
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
import database
import medical_engine

class TestMedBuddyMasterVerification(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize and seed database before running test cases."""
        database.init_db()
        database.seed_demo_data()
        cls.client = app.test_client()

    # -------------------------------------------------------------
    # GRAND MODULE 1: Patient Identity & Profile
    # -------------------------------------------------------------
    def test_01_patient_dashboard_and_profile(self):
        """Verifies patient profile retrieval, greeting data, and metric counts."""
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["patient"]["name"], "Kashish Sharma")
        self.assertIn("active_medications", data["metrics"])
        self.assertGreaterEqual(data["metrics"]["active_medications"], 1)

    def test_01b_profile_update_and_logout(self):
        """Verifies GET /api/profile, POST /api/profile, and auth logout/login endpoints."""
        # Get profile
        r_get = self.client.get("/api/profile")
        self.assertEqual(r_get.status_code, 200)
        p = json.loads(r_get.data)["profile"]
        self.assertEqual(p["name"], "Kashish Sharma")
        self.assertIn("phone", p)
        self.assertIn("allergies", p)

        # Update profile
        r_post = self.client.post("/api/profile", json={
            "name": "Kashish Sharma",
            "email": "kashish.sharma@example.com",
            "phone": "+91 98765 43210",
            "age": 35,
            "gender": "Female",
            "blood_group": "B+",
            "allergies": "Penicillin",
            "chronic_conditions": "Type 2 Diabetes Mellitus",
            "emergency_contact": "Rohan Sharma (+91 98765 43211)",
            "preferred_language": "en",
            "reading_level": "standard"
        })
        self.assertEqual(r_post.status_code, 200)
        self.assertEqual(json.loads(r_post.data)["status"], "success")

        # Logout
        r_logout = self.client.post("/api/auth/logout")
        self.assertEqual(r_logout.status_code, 200)

        # Login
        r_login = self.client.post("/api/auth/login", json={"name": "Kashish Sharma"})
        self.assertEqual(r_login.status_code, 200)

    # -------------------------------------------------------------
    # GRAND MODULE 2: Medical File Ingestion & Strict Classifier
    # -------------------------------------------------------------
    def test_02_medical_report_validation_positive(self):
        """Verifies that an authentic medical lab report is accepted."""
        pdf_path = os.path.join(PROJECT_ROOT, "sample_data", "sample_cbc_lab_report.pdf")
        self.assertTrue(os.path.exists(pdf_path), "sample_cbc_lab_report.pdf must exist")
        
        val = medical_engine.validate_and_classify_medical_file(pdf_path, "sample_cbc_lab_report.pdf", "application/pdf")
        self.assertTrue(val["is_valid"], "Authentic lab report must be marked valid")
        self.assertTrue(val["is_medical"], "Authentic lab report must be classified as medical")
        self.assertGreaterEqual(val["confidence_score"], 60)

    def test_03_non_medical_invoice_rejection_negative(self):
        """Verifies that a retail tax invoice is strictly REJECTED (Feature 3)."""
        inv_path = os.path.join(PROJECT_ROOT, "sample_data", "sample_non_medical_invoice.pdf")
        self.assertTrue(os.path.exists(inv_path), "sample_non_medical_invoice.pdf must exist")
        
        val = medical_engine.validate_and_classify_medical_file(inv_path, "sample_non_medical_invoice.pdf", "application/pdf")
        self.assertFalse(val["is_medical"], "Non-medical invoice must NOT be classified as medical")
        
        # Test API endpoint rejection
        res = self.client.post("/api/reports/sample/non_medical")
        self.assertEqual(res.status_code, 422, "Non-medical file must return HTTP 422")
        data = json.loads(res.data)
        self.assertEqual(data["status"], "rejected")
        self.assertFalse(data["is_medical"])

    # -------------------------------------------------------------
    # GRAND MODULE 3: Document Text Extraction & OCR
    # -------------------------------------------------------------
    def test_04_digital_pdf_and_ocr_extraction(self):
        """Verifies text extraction from digital PDF and OCR image."""
        pdf_path = os.path.join(PROJECT_ROOT, "sample_data", "sample_cbc_lab_report.pdf")
        text = medical_engine.extract_text_from_pdf(pdf_path)
        self.assertIn("METROPOLIS", text.upper())
        self.assertIn("GLUCOSE", text.upper())

        img_path = os.path.join(PROJECT_ROOT, "sample_data", "sample_prescription.png")
        if os.path.exists(img_path) and os.path.exists(medical_engine.TESSERACT_PATH):
            ocr_text = medical_engine.extract_text_from_image(img_path)
            self.assertIn("METFORMIN", ocr_text.upper())

    # -------------------------------------------------------------
    # GRAND MODULE 4: Deterministic Lab Value Status & Reference Bounds
    # -------------------------------------------------------------
    def test_05_deterministic_lab_value_evaluation(self):
        """Verifies that numerical lab results are deterministically compared to printed bounds."""
        res = self.client.post("/api/reports/sample/standard_lab")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        lab_results = data["lab_results"]
        self.assertGreaterEqual(len(lab_results), 5)

        # Check Glucose (142 mg/dL vs 70-99 mg/dL -> High)
        glucose = next((x for x in lab_results if "Glucose" in x["test_name"]), None)
        self.assertIsNotNone(glucose)
        self.assertEqual(glucose["value"], 142.0)
        self.assertEqual(glucose["status"], "High")

        # Check Creatinine (0.85 mg/dL vs 0.6-1.2 mg/dL -> Within Range)
        creat = next((x for x in lab_results if "Creatinine" in x["test_name"]), None)
        self.assertIsNotNone(creat)
        self.assertEqual(creat["status"], "Within Range")

    # -------------------------------------------------------------
    # GRAND MODULE 5: Clinical Safety & Red-Flag Alerts
    # -------------------------------------------------------------
    def test_06_critical_red_flag_detection(self):
        """Verifies that severe clinical thresholds trigger urgent red-flag alerts."""
        res = self.client.post("/api/reports/sample/critical_alert")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        red_flags = data["red_flags"]
        
        # Must detect critical alerts
        self.assertGreaterEqual(len(red_flags), 3, "Emergency report must trigger at least 3 critical red-flags")
        flagged_tests = [rf["test"] for rf in red_flags]
        self.assertTrue(any("Glucose" in t for t in flagged_tests), "Critical glucose must be flagged")
        self.assertTrue(any("Potassium" in t for t in flagged_tests), "Critical potassium must be flagged")
        self.assertTrue(any("Hemoglobin" in t for t in flagged_tests), "Critical low hemoglobin must be flagged")

    # -------------------------------------------------------------
    # GRAND MODULE 6: Plain-Language Terms & Jargon Glossary
    # -------------------------------------------------------------
    def test_07_medical_jargon_explainer(self):
        """Verifies that difficult clinical terms return plain-language layperson explanations."""
        self.assertIn("hba1c", medical_engine.MEDICAL_JARGON_GLOSSARY)
        hba1c_info = medical_engine.MEDICAL_JARGON_GLOSSARY["hba1c"]
        self.assertIn("plain", hba1c_info)
        self.assertIn("sugar", hba1c_info["plain"].lower())

    # -------------------------------------------------------------
    # GRAND MODULE 7: Reading Level Adaptation
    # -------------------------------------------------------------
    def test_08_reading_level_adaptation(self):
        """Verifies that Simple, Standard, and Detailed reading levels generate valid content."""
        sample_abnormal = [{"test_name": "Blood Glucose", "value": 142, "unit": "mg/dL", "status": "High"}]
        
        simple_res = self.client.post("/api/explanations/reading-level", json={
            "level": "simple",
            "base_summary": "Your glucose is high.",
            "abnormal_items": sample_abnormal
        })
        self.assertEqual(simple_res.status_code, 200)
        simple_text = json.loads(simple_res.data)["adapted_text"]
        self.assertIn("Everyday Words", simple_text)

        detailed_res = self.client.post("/api/explanations/reading-level", json={
            "level": "detailed",
            "base_summary": "Your glucose is high.",
            "abnormal_items": sample_abnormal
        })
        self.assertEqual(detailed_res.status_code, 200)
        detailed_text = json.loads(detailed_res.data)["adapted_text"]
        self.assertIn("Clinical & Biological Interpretation", detailed_text)

    # -------------------------------------------------------------
    # GRAND MODULE 8: Multilingual Translation (EN, HI, KN)
    # -------------------------------------------------------------
    def test_09_multilingual_translation_and_unit_preservation(self):
        """Verifies Hindi and Kannada translation preserves numbers and medical units."""
        text = "Your comprehensive blood test shows fasting blood sugar (Glucose) is 142 mg/dL."
        
        # Test Hindi
        res_hi = self.client.post("/api/explanations/translate", json={"text": text, "language": "hi"})
        self.assertEqual(res_hi.status_code, 200)
        trans_hi = json.loads(res_hi.data)["translated_text"]
        self.assertIn("142 mg/dL", trans_hi, "Numbers and units must not be corrupted during translation")

        # Test Kannada
        res_kn = self.client.post("/api/explanations/translate", json={"text": text, "language": "kn"})
        self.assertEqual(res_kn.status_code, 200)
        trans_kn = json.loads(res_kn.data)["translated_text"]
        self.assertIn("142 mg/dL", trans_kn, "Numbers and units must not be corrupted in Kannada")

    # -------------------------------------------------------------
    # GRAND MODULE 9: Medication Explainer & Schedule Reminders
    # -------------------------------------------------------------
    def test_10_medicines_and_reminders(self):
        """Verifies medication lookup, purpose, precautions, and reminder toggles."""
        # Medicine lookup
        res_med = self.client.get("/api/medicines/explain/Metformin")
        self.assertEqual(res_med.status_code, 200)
        info = json.loads(res_med.data)["medicine_info"]
        self.assertIn("insulin", info["purpose"].lower())
        self.assertIn("meals", info["timing"].lower())

        # Reminders list
        res_rem = self.client.get("/api/reminders")
        self.assertEqual(res_rem.status_code, 200)
        reminders = json.loads(res_rem.data)["reminders"]
        self.assertGreaterEqual(len(reminders), 1)

        # Toggle reminder
        r_id = reminders[0]["reminder_id"]
        res_toggle = self.client.post(f"/api/reminders/{r_id}/toggle")
        self.assertEqual(res_toggle.status_code, 200)
        self.assertIn(json.loads(res_toggle.data)["new_status"], ["taken", "pending"])

    # -------------------------------------------------------------
    # GRAND MODULE 10: Family Caregiver Access & Audit Logging
    # -------------------------------------------------------------
    def test_11_family_access_and_audit_trail(self):
        """Verifies caregiver permission toggling and immutable audit logging."""
        # Family list
        res_fam = self.client.get("/api/family")
        self.assertEqual(res_fam.status_code, 200)
        members = json.loads(res_fam.data)["family_members"]
        self.assertGreaterEqual(len(members), 1)

        # Toggle access revocation
        m_id = members[0]["access_id"]
        res_toggle = self.client.post(f"/api/family/{m_id}/toggle")
        self.assertEqual(res_toggle.status_code, 200)

        # Check Audit log has recorded entries
        res_audit = self.client.get("/api/audit-logs")
        self.assertEqual(res_audit.status_code, 200)
        logs = json.loads(res_audit.data)["logs"]
        self.assertGreaterEqual(len(logs), 1)

    # -------------------------------------------------------------
    # GRAND MODULE 11: Contextual Doctor Questions Generator
    # -------------------------------------------------------------
    def test_12_doctor_questions_generation(self):
        """Verifies that abnormal test results generate tailored doctor consultation questions."""
        sample_abnormal = [
            {"test_name": "Fasting Blood Glucose", "value": 142, "unit": "mg/dL"},
            {"test_name": "LDL Cholesterol", "value": 148, "unit": "mg/dL"}
        ]
        questions = medical_engine.generate_doctor_questions(sample_abnormal)
        self.assertGreaterEqual(len(questions), 2)
        q_str = " ".join(questions)
        self.assertTrue("sugar" in q_str.lower() or "diet" in q_str.lower() or "glucose" in q_str.lower())
        self.assertTrue("cholesterol" in q_str.lower() or "statin" in q_str.lower())

if __name__ == "__main__":
    unittest.main()
