"""
MedBuddy - AI-Powered Multilingual Medical Report Assistant MVP
Flask Backend Server implementing all 12 core PRD features.
"""

import os
import json
import uuid
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

import database
import medical_engine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "medbuddy-dev-secret-key-2026"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# CORS headers
@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return resp

# -------------------------------------------------------------
# Frontend Route
# -------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# -------------------------------------------------------------
# Feature 7: Dashboard Summary
# -------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    conn = database.get_connection()
    cur = conn.cursor()

    patient_id = "pat_kashish_001"

    # Profile
    cur.execute("SELECT * FROM patient_profiles WHERE patient_id = ?", (patient_id,))
    profile_row = cur.fetchone()
    cur.execute("SELECT name, email FROM users WHERE user_id = ?", (profile_row["user_id"],))
    user_row = cur.fetchone()

    # Active medications
    cur.execute("SELECT COUNT(*) FROM medicines WHERE patient_id = ? AND active = 1", (patient_id,))
    active_meds = cur.fetchone()[0]

    # Reminders today
    cur.execute("SELECT * FROM reminders WHERE patient_id = ?", (patient_id,))
    reminders = [dict(r) for r in cur.fetchall()]
    taken_today = sum(1 for r in reminders if r["status"] == "taken" and r["reminder_type"] == "medicine")
    total_med_doses = sum(1 for r in reminders if r["reminder_type"] == "medicine")
    overdue = sum(1 for r in reminders if r["status"] == "missed")

    # Recent reports
    cur.execute("SELECT * FROM medical_reports WHERE patient_id = ? ORDER BY created_at DESC LIMIT 5", (patient_id,))
    recent_reports = [dict(r) for r in cur.fetchall()]

    # Red flag alerts
    cur.execute("""
        SELECT lv.*, mr.file_name 
        FROM lab_values lv
        JOIN medical_reports mr ON lv.report_id = mr.report_id
        WHERE mr.patient_id = ? AND lv.severity = 'danger'
    """, (patient_id,))
    critical_alerts = [dict(r) for r in cur.fetchall()]

    conn.close()

    return jsonify({
        "status": "success",
        "patient": {
            "name": user_row["name"],
            "email": user_row["email"],
            "age": profile_row["age"],
            "gender": profile_row["gender"],
            "blood_group": profile_row["blood_group"],
            "allergies": profile_row["allergies"],
            "preferred_language": profile_row["preferred_language"],
            "reading_level": profile_row["reading_level"]
        },
        "metrics": {
            "active_medications": active_meds,
            "taken_today": f"{taken_today}/{total_med_doses}",
            "overdue": overdue,
            "pending_orders": 0,
            "total_reports": len(recent_reports),
            "critical_alerts_count": len(critical_alerts)
        },
        "today_doses": reminders,
        "recent_reports": recent_reports,
        "critical_alerts": critical_alerts
    })

# -------------------------------------------------------------
# Feature 3: File Upload & Strict Medical Validation
# -------------------------------------------------------------
@app.route("/api/reports/upload", methods=["POST"])
def upload_report():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4()}_{filename}")
    file.save(save_path)

    # Validate medical file (Feature 3)
    validation = medical_engine.validate_and_classify_medical_file(save_path, filename, file.content_type)
    
    if not validation["is_valid"] or not validation["is_medical"]:
        # Log rejected attempt
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "user_kashish_001", "UPLOAD_REJECTED", filename, validation["reason"]))
        conn.commit()
        conn.close()

        # Clean up rejected file
        try:
            os.remove(save_path)
        except Exception:
            pass

        return jsonify({
            "status": "rejected",
            "is_medical": False,
            "confidence_score": validation.get("confidence_score", 0),
            "message": validation["reason"]
        }), 422

    # Process valid medical document
    raw_text = validation["raw_text"]
    lab_results, red_flags = medical_engine.parse_lab_values_from_text(raw_text)

    # Detect jargon
    detected_jargon = []
    text_lower = raw_text.lower()
    for k, j_info in medical_engine.MEDICAL_JARGON_GLOSSARY.items():
        if k in text_lower:
            detected_jargon.append(j_info)

    # Determine summary
    abnormal = [r for r in lab_results if r["status"] != "Within Range"]
    if len(abnormal) > 0:
        ab_names = ", ".join([f"{x['test_name']} ({x['value']} {x['unit']})" for x in abnormal[:3]])
        base_summary = f"Your medical test results were successfully analyzed. Most parameters are noted, but {len(abnormal)} test(s) showed out-of-range values: {ab_names}. We recommend sharing these findings with your consulting physician."
    else:
        base_summary = "Your medical report has been processed. All extracted laboratory parameters fall comfortably within standard reference intervals."

    doctor_questions = medical_engine.generate_doctor_questions(abnormal)

    # Save to database
    report_id = f"rep_{uuid.uuid4().hex[:8]}"
    patient_id = "pat_kashish_001"

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO medical_reports (report_id, patient_id, file_name, file_path, file_type, report_type, report_date, processing_status, is_medical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (report_id, patient_id, filename, save_path, file.content_type or "application/pdf", "Laboratory Investigation", date.today().isoformat(), "Completed"))

    cur.execute("""
        INSERT INTO report_explanations (explanation_id, report_id, language, reading_level, extracted_text, summary_text, jargon_explained, doctor_questions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()), report_id, "en", "standard",
        raw_text[:2000],
        base_summary,
        json.dumps(detected_jargon),
        json.dumps(doctor_questions)
    ))

    for lr in lab_results:
        cur.execute("""
            INSERT INTO lab_values (value_id, report_id, test_name, value, unit, reference_low, reference_high, status, severity, clinical_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), report_id, lr["test_name"], lr["value"], lr["unit"], lr["reference_low"], lr["reference_high"], lr["status"], lr["severity"], lr.get("alert_text") or ""))

    # Audit log
    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "REPORT_UPLOAD_SUCCESS", report_id, f"Uploaded {filename} with {len(lab_results)} extracted lab values."))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "report_id": report_id,
        "is_medical": True,
        "confidence_score": validation.get("confidence_score", 95),
        "file_name": filename,
        "lab_results": lab_results,
        "red_flags": red_flags,
        "jargon_explained": detected_jargon,
        "summary": base_summary,
        "doctor_questions": doctor_questions
    })

# -------------------------------------------------------------
# Quick Sample Loader (For Instant Testing)
# -------------------------------------------------------------
@app.route("/api/reports/sample/<sample_type>", methods=["POST"])
def load_sample_report(sample_type):
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    
    mapping = {
        "standard_lab": ("sample_cbc_lab_report.pdf", "application/pdf"),
        "critical_alert": ("sample_critical_redflag_report.pdf", "application/pdf"),
        "non_medical": ("sample_non_medical_invoice.pdf", "application/pdf"),
        "prescription_image": ("sample_prescription.png", "image/png")
    }

    if sample_type not in mapping:
        return jsonify({"status": "error", "message": "Unknown sample type"}), 400

    filename, mime = mapping[sample_type]
    file_path = os.path.join(sample_dir, filename)

    validation = medical_engine.validate_and_classify_medical_file(file_path, filename, mime)

    if not validation["is_valid"] or not validation["is_medical"]:
        return jsonify({
            "status": "rejected",
            "is_medical": False,
            "sample_type": sample_type,
            "file_name": filename,
            "confidence_score": validation.get("confidence_score", 0),
            "message": validation["reason"]
        }), 422

    raw_text = validation["raw_text"]
    lab_results, red_flags = medical_engine.parse_lab_values_from_text(raw_text)

    detected_jargon = []
    text_lower = raw_text.lower()
    for k, j_info in medical_engine.MEDICAL_JARGON_GLOSSARY.items():
        if k in text_lower:
            detected_jargon.append(j_info)

    abnormal = [r for r in lab_results if r["status"] != "Within Range"]
    if len(red_flags) > 0:
        base_summary = f"CRITICAL NOTICE: This report contains {len(red_flags)} urgent red-flag values that exceed clinical safety limits. Please consult an emergency physician or doctor promptly."
    elif len(abnormal) > 0:
        base_summary = f"Your lab results have been reviewed. {len(abnormal)} tests are outside reference ranges. Follow-up is recommended to monitor your health markers."
    else:
        base_summary = "Your report shows all tested parameters are within standard healthy ranges."

    doctor_questions = medical_engine.generate_doctor_questions(abnormal)

    return jsonify({
        "status": "success",
        "sample_type": sample_type,
        "is_medical": True,
        "confidence_score": validation.get("confidence_score", 95),
        "file_name": filename,
        "lab_results": lab_results,
        "red_flags": red_flags,
        "jargon_explained": detected_jargon,
        "summary": base_summary,
        "doctor_questions": doctor_questions
    })

# -------------------------------------------------------------
# Feature 11: Reading Level Switching
# -------------------------------------------------------------
@app.route("/api/explanations/reading-level", methods=["POST"])
def change_reading_level():
    data = request.json or {}
    level = data.get("level", "standard") # simple, standard, detailed
    summary = data.get("base_summary", "Your test report summary.")
    abnormal = data.get("abnormal_items", [])

    adapted = medical_engine.adapt_explanation_to_reading_level(summary, abnormal, level)

    return jsonify({
        "status": "success",
        "level": level,
        "adapted_text": adapted
    })

# -------------------------------------------------------------
# Feature 2: Multilingual Translation
# -------------------------------------------------------------
@app.route("/api/explanations/translate", methods=["POST"])
def translate_explanation():
    data = request.json or {}
    text = data.get("text", "")
    target_lang = data.get("language", "en") # 'en', 'hi', 'kn'

    translated = medical_engine.translate_content(text, target_lang)
    lang_labels = medical_engine.TRANSLATION_MAP.get(target_lang, {})

    return jsonify({
        "status": "success",
        "language": target_lang,
        "translated_text": translated,
        "ui_labels": lang_labels
    })

# -------------------------------------------------------------
# Feature 9: Medicine Explainer & Management
# -------------------------------------------------------------
@app.route("/api/medicines", methods=["GET"])
def get_medicines():
    patient_id = "pat_kashish_001"
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medicines WHERE patient_id = ?", (patient_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"status": "success", "medicines": rows})

@app.route("/api/medicines/explain/<name>", methods=["GET"])
def explain_med(name):
    info = medical_engine.explain_medicine(name)
    return jsonify({"status": "success", "medicine_info": info})

# -------------------------------------------------------------
# Feature 6: Reminders (Medicine & Doctor Appointments)
# -------------------------------------------------------------
@app.route("/api/reminders", methods=["GET", "POST"])
def handle_reminders():
    patient_id = "pat_kashish_001"
    conn = database.get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        data = request.json or {}
        r_type = data.get("reminder_type", "medicine")
        title = data.get("title", "New Dose")
        subtitle = data.get("subtitle", "Scheduled")
        scheduled_time = data.get("scheduled_time", "08:00 AM")
        date_for = data.get("date_for", date.today().isoformat())

        r_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO reminders (reminder_id, patient_id, reminder_type, title, subtitle, scheduled_time, status, date_for)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (r_id, patient_id, r_type, title, subtitle, scheduled_time, date_for))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "reminder_id": r_id, "message": "Reminder created successfully"})

    cur.execute("SELECT * FROM reminders WHERE patient_id = ? ORDER BY scheduled_time ASC", (patient_id,))
    reminders = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"status": "success", "reminders": reminders})

@app.route("/api/reminders/<reminder_id>/toggle", methods=["POST"])
def toggle_reminder_status(reminder_id):
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM reminders WHERE reminder_id = ?", (reminder_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Reminder not found"}), 404

    new_status = "taken" if row["status"] != "taken" else "pending"
    cur.execute("UPDATE reminders SET status = ? WHERE reminder_id = ?", (new_status, reminder_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "new_status": new_status})

# -------------------------------------------------------------
# Feature 5: Family Caregiver Access & Permissions
# -------------------------------------------------------------
@app.route("/api/family", methods=["GET"])
def get_family_members():
    patient_id = "pat_kashish_001"
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM family_access WHERE patient_id = ?", (patient_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"status": "success", "family_members": rows})

@app.route("/api/family/invite", methods=["POST"])
def invite_family_member():
    data = request.json or {}
    patient_id = "pat_kashish_001"
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    relation = data.get("relation", "Family Member")
    permission = data.get("permission", "view_all")

    if not name or not email:
        return jsonify({"status": "error", "message": "Name and email are required"}), 400

    conn = database.get_connection()
    cur = conn.cursor()
    access_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO family_access (access_id, patient_id, member_name, member_email, relation, permission, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (access_id, patient_id, name, email, relation, permission))

    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "FAMILY_ACCESS_GRANTED", access_id, f"Granted {permission} access to {name} ({email})"))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "access_id": access_id, "message": f"Invitation and access granted to {name}"})

@app.route("/api/family/<access_id>/toggle", methods=["POST"])
def toggle_family_access(access_id):
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, member_name FROM family_access WHERE access_id = ?", (access_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Member not found"}), 404

    new_status = "revoked" if row["status"] == "active" else "active"
    cur.execute("UPDATE family_access SET status = ? WHERE access_id = ?", (new_status, access_id))

    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "FAMILY_ACCESS_REVOKED" if new_status == "revoked" else "FAMILY_ACCESS_RESTORED", access_id, f"Access {new_status} for {row['member_name']}"))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "new_status": new_status})

# -------------------------------------------------------------
# Audit Logs
# -------------------------------------------------------------
@app.route("/api/audit-logs", methods=["GET"])
def get_audit_logs():
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"status": "success", "logs": rows})

# -------------------------------------------------------------
# Feature: Patient Health Profile & Authentication
# -------------------------------------------------------------
@app.route("/api/profile", methods=["GET"])
def get_profile():
    patient_id = "pat_kashish_001"
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patient_profiles WHERE patient_id = ?", (patient_id,))
    p_row = dict(cur.fetchone() or {})
    cur.execute("SELECT name, email, role FROM users WHERE user_id = ?", (p_row.get("user_id"),))
    u_row = dict(cur.fetchone() or {})
    conn.close()

    return jsonify({
        "status": "success",
        "profile": {
            "patient_id": patient_id,
            "name": u_row.get("name", "Kashish Sharma"),
            "email": u_row.get("email", "kashish.sharma@example.com"),
            "role": u_row.get("role", "patient"),
            "age": p_row.get("age", 34),
            "gender": p_row.get("gender", "Female"),
            "phone": p_row.get("phone") or "+91 98765 43210",
            "blood_group": p_row.get("blood_group", "B+"),
            "allergies": p_row.get("allergies", "Penicillin"),
            "chronic_conditions": p_row.get("chronic_conditions") or "Type 2 Diabetes Mellitus, Mild Dyslipidemia",
            "emergency_contact": p_row.get("emergency_contact") or "Rohan Sharma (Spouse) - +91 98765 43211",
            "preferred_language": p_row.get("preferred_language", "en"),
            "reading_level": p_row.get("reading_level", "standard"),
            "created_at": p_row.get("created_at")
        }
    })

@app.route("/api/profile", methods=["POST"])
def update_profile():
    data = request.json or {}
    patient_id = "pat_kashish_001"
    name = data.get("name", "Kashish Sharma")
    email = data.get("email", "kashish.sharma@example.com")
    age = data.get("age", 34)
    gender = data.get("gender", "Female")
    phone = data.get("phone", "+91 98765 43210")
    blood_group = data.get("blood_group", "B+")
    allergies = data.get("allergies", "Penicillin")
    chronic_conditions = data.get("chronic_conditions", "Type 2 Diabetes Mellitus, Mild Dyslipidemia")
    emergency_contact = data.get("emergency_contact", "Rohan Sharma (Spouse) - +91 98765 43211")
    preferred_language = data.get("preferred_language", "en")
    reading_level = data.get("reading_level", "standard")

    conn = database.get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users SET name = ?, email = ?
        WHERE user_id = (SELECT user_id FROM patient_profiles WHERE patient_id = ?)
    """, (name, email, patient_id))

    cur.execute("""
        UPDATE patient_profiles 
        SET age = ?, gender = ?, phone = ?, blood_group = ?, allergies = ?, 
            chronic_conditions = ?, emergency_contact = ?, preferred_language = ?, reading_level = ?
        WHERE patient_id = ?
    """, (age, gender, phone, blood_group, allergies, chronic_conditions, emergency_contact, preferred_language, reading_level, patient_id))

    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "PROFILE_UPDATED", patient_id, f"Patient personal details and clinical baseline updated for {name}"))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Profile updated successfully"})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "USER_LOGOUT", "session_active", "User session ended / logged out"))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Logged out successfully"})

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    name = data.get("name", "Kashish Sharma")
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO audit_logs (log_id, user_id, action, record_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), "user_kashish_001", "USER_LOGIN", "session_new", f"User {name} authenticated successfully"))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Welcome back, {name}!", "user": name})

if __name__ == "__main__":
    database.init_db()
    database.seed_demo_data()
    print("MedBuddy MVP Backend running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
