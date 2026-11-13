"""
Database module for AI Medical Report Assistant (MedBuddy MVP).
Implements relational storage conforming to PRD specifications:
- users
- patient_profiles
- medical_reports
- report_explanations
- lab_values
- medicines
- appointments
- reminders
- family_access
- audit_logs
"""

import sqlite3
import os
import uuid
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "medbuddy.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'patient',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Patient profiles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patient_profiles (
        patient_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        preferred_language TEXT DEFAULT 'en',
        reading_level TEXT DEFAULT 'standard',
        blood_group TEXT,
        allergies TEXT,
        phone TEXT,
        emergency_contact TEXT,
        chronic_conditions TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Ensure optional columns exist if migrating from previous schema
    for col in ["phone", "emergency_contact", "chronic_conditions"]:
        try:
            cur.execute(f"ALTER TABLE patient_profiles ADD COLUMN {col} TEXT")
        except Exception:
            pass

    # Ensure baseline profile defaults for demo patient
    try:
        cur.execute("""
            UPDATE patient_profiles 
            SET phone = COALESCE(phone, '+91 98765 43210'),
                emergency_contact = COALESCE(emergency_contact, 'Rohan Sharma (Spouse) - +91 98765 43211'),
                chronic_conditions = COALESCE(chronic_conditions, 'Type 2 Diabetes Mellitus, Mild Dyslipidemia')
            WHERE patient_id = 'pat_kashish_001'
        """)
    except Exception:
        pass

    # Medical reports
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medical_reports (
        report_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        report_type TEXT DEFAULT 'Laboratory Report',
        report_date DATE,
        processing_status TEXT DEFAULT 'Completed',
        is_medical BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
    )
    """)

    # Report explanations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS report_explanations (
        explanation_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        language TEXT DEFAULT 'en',
        reading_level TEXT DEFAULT 'standard',
        extracted_text TEXT,
        summary_text TEXT,
        key_findings TEXT,
        jargon_explained TEXT,
        doctor_questions TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES medical_reports(report_id)
    )
    """)

    # Lab values
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lab_values (
        value_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        test_name TEXT NOT NULL,
        value REAL NOT NULL,
        unit TEXT,
        reference_low REAL,
        reference_high REAL,
        status TEXT,
        severity TEXT DEFAULT 'normal',
        clinical_note TEXT,
        FOREIGN KEY (report_id) REFERENCES medical_reports(report_id)
    )
    """)

    # Medicines
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        medicine_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        report_id TEXT,
        medicine_name TEXT NOT NULL,
        dosage TEXT,
        frequency TEXT,
        timing_instructions TEXT,
        purpose TEXT,
        precautions TEXT,
        start_date DATE,
        end_date DATE,
        active BOOLEAN DEFAULT 1,
        FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
    )
    """)

    # Appointments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        specialty TEXT,
        clinic_hospital TEXT,
        appointment_date TIMESTAMP NOT NULL,
        purpose TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Scheduled',
        FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
    )
    """)

    # Reminders
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        reminder_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        reminder_type TEXT NOT NULL, -- 'medicine' or 'appointment'
        title TEXT NOT NULL,
        subtitle TEXT,
        scheduled_time TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- 'pending', 'taken', 'missed'
        date_for DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
    )
    """)

    # Family Access
    cur.execute("""
    CREATE TABLE IF NOT EXISTS family_access (
        access_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        member_name TEXT NOT NULL,
        member_email TEXT NOT NULL,
        relation TEXT NOT NULL,
        permission TEXT DEFAULT 'view_all', -- 'view_all', 'view_reports_only', 'manage_reminders'
        status TEXT DEFAULT 'active', -- 'active', 'revoked'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
    )
    """)

    # Audit Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        action TEXT NOT NULL,
        record_id TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def seed_demo_data():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        conn.close()
        return  # already seeded

    user_id = "user_kashish_001"
    patient_id = "pat_kashish_001"

    # 1. Create Patient User
    cur.execute("""
        INSERT INTO users (user_id, name, email, role)
        VALUES (?, ?, ?, ?)
    """, (user_id, "Kashish Sharma", "kashish.sharma@example.com", "patient"))

    cur.execute("""
        INSERT INTO patient_profiles (patient_id, user_id, age, gender, preferred_language, reading_level, blood_group, allergies)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, user_id, 34, "Female", "en", "standard", "B+", "Penicillin"))

    # 2. Pre-seed a Medical Lab Report
    rep_id = "rep_cbc_lipid_001"
    cur.execute("""
        INSERT INTO medical_reports (report_id, patient_id, file_name, file_path, file_type, report_type, report_date, processing_status, is_medical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (rep_id, patient_id, "Comprehensive_Metabolic_Lipid_Panel.pdf", "sample_data/Comprehensive_Metabolic_Lipid_Panel.pdf", "application/pdf", "Laboratory Report", "2026-11-10", "Completed", 1))

    # Explanation for report
    summary = ("Your comprehensive blood test shows that your kidney function and liver enzymes are healthy. "
               "However, your fasting blood sugar (Glucose) and HbA1c are higher than standard target ranges, "
               "suggesting mild diabetes progression. Additionally, your LDL ('bad') cholesterol is slightly elevated. "
               "These values require follow-up with your doctor to discuss medication adjustment and diet.")
    
    jargon = [
        {"term": "HbA1c (Glycated Hemoglobin)", "plain": "Average blood sugar level over the past 3 months. Normal is under 5.7%."},
        {"term": "LDL Cholesterol", "plain": "'Bad' cholesterol that can build up in blood vessels if too high."},
        {"term": "Serum Creatinine", "plain": "A waste product filtered out by your kidneys. A normal value means your kidneys are filtering well."},
        {"term": "Bilirubin", "plain": "A yellowish substance produced when red blood cells break down, checked for liver health."}
    ]
    import json
    cur.execute("""
        INSERT INTO report_explanations (explanation_id, report_id, language, reading_level, extracted_text, summary_text, jargon_explained, doctor_questions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()), rep_id, "en", "standard",
        "Sample verified text from clinical laboratory panel.",
        summary,
        json.dumps(jargon),
        json.dumps([
            "My HbA1c is 7.4%. What diet and lifestyle adjustments do you recommend first?",
            "Do I need to start or adjust medicine for my LDL cholesterol of 148 mg/dL?",
            "When should I repeat this blood panel to check if my numbers are improving?"
        ])
    ))

    # Lab values
    lab_items = [
        ("Fasting Blood Glucose", 142, "mg/dL", 70.0, 99.0, "High", "warning", "Fasting blood sugar is above normal range (70-99 mg/dL)."),
        ("HbA1c", 7.4, "%", 4.0, 5.6, "High", "warning", "Elevated 3-month sugar average indicates need for diabetic glycemic management."),
        ("Total Cholesterol", 228, "mg/dL", 125.0, 200.0, "High", "warning", "Slightly elevated total lipid level."),
        ("LDL Cholesterol", 148, "mg/dL", 0.0, 100.0, "High", "warning", "'Bad' cholesterol is elevated above recommended target."),
        ("HDL Cholesterol", 46, "mg/dL", 40.0, 60.0, "Normal", "normal", "Protective 'good' cholesterol is in a healthy range."),
        ("Serum Creatinine", 0.85, "mg/dL", 0.6, 1.2, "Normal", "normal", "Healthy kidney filtration indicator."),
        ("Hemoglobin (Hb)", 13.2, "g/dL", 12.0, 15.5, "Normal", "normal", "Healthy red blood cell oxygen carrying capacity.")
    ]
    for item in lab_items:
        cur.execute("""
            INSERT INTO lab_values (value_id, report_id, test_name, value, unit, reference_low, reference_high, status, severity, clinical_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), rep_id, item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7]))

    # 3. Pre-seed Active Medicines
    meds = [
        ("Metformin 500mg", "500 mg", "Twice daily (BD)", "Take with morning and evening meals", "Helps lower blood sugar by improving insulin sensitivity", "Do not skip meals; drink plenty of water"),
        ("Atorvastatin 10mg", "10 mg", "Once daily (HS)", "Take at bedtime", "Lowers LDL ('bad') cholesterol and protects blood vessels", "Avoid grapefruit juice; report unexplained muscle soreness"),
        ("Vitamin D3 60,000 IU", "60,000 IU", "Once weekly", "Take after Sunday lunch with milk/water", "Restores bone and immune health", "Weekly dose only; do not take daily"),
        ("Pantoprazole 40mg", "40 mg", "Once daily", "Take 30 mins before morning breakfast", "Reduces stomach acid and prevents gastric irritation", "Take on an empty stomach")
    ]
    for m in meds:
        cur.execute("""
            INSERT INTO medicines (medicine_id, patient_id, report_id, medicine_name, dosage, frequency, timing_instructions, purpose, precautions, start_date, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (str(uuid.uuid4()), patient_id, rep_id, m[0], m[1], m[2], m[3], m[4], m[5], "2026-11-01"))

    # 4. Pre-seed Reminders for Today
    today_str = date.today().isoformat()
    reminders = [
        ("medicine", "Morning Dose: Pantoprazole 40mg", "Take 30 mins before breakfast", "07:30 AM", "taken", today_str),
        ("medicine", "Morning Dose: Metformin 500mg", "Take with breakfast", "08:30 AM", "taken", today_str),
        ("medicine", "Afternoon Dose: Vitamin D3 (Weekly)", "After lunch", "01:30 PM", "taken", today_str),
        ("medicine", "Night Dose: Metformin 500mg & Atorvastatin", "Take after dinner & at bedtime", "09:00 PM", "pending", today_str),
        ("appointment", "Follow-up with Dr. Arvind Kumar", "Endocrinologist - Apollo Health City", "11:00 AM (Next Tuesday)", "pending", today_str)
    ]
    for r in reminders:
        cur.execute("""
            INSERT INTO reminders (reminder_id, patient_id, reminder_type, title, subtitle, scheduled_time, status, date_for)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), patient_id, r[0], r[1], r[2], r[3], r[4], r[5]))

    # 5. Pre-seed Appointments
    cur.execute("""
        INSERT INTO appointments (appointment_id, patient_id, doctor_name, specialty, clinic_hospital, appointment_date, purpose, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), patient_id, "Dr. Arvind Kumar", "Endocrinologist", "Apollo Health City, OPD Block 3", "2026-11-18 11:00:00", "Quarterly Diabetic Review & Lipid Check", "Carry previous blood panel reports", "Scheduled"))

    # 6. Pre-seed Family Member Access
    cur.execute("""
        INSERT INTO family_access (access_id, patient_id, member_name, member_email, relation, permission, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), patient_id, "Rohan Sharma", "rohan.sharma@example.com", "Spouse / Caregiver", "view_all", "active"))
    cur.execute("""
        INSERT INTO family_access (access_id, patient_id, member_name, member_email, relation, permission, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), patient_id, "Sunita Sharma", "sunita.s@example.com", "Mother", "view_reports_only", "active"))

    # 7. Audit log entry
    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), user_id, "SYSTEM_INIT", rep_id, "Demo patient profile and lab report initialized."))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("Database initialized and demo data seeded successfully!")
