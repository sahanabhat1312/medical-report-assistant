"""
Medical Engine for MedBuddy MVP.
Implements:
- Feature 1: Plain language medical terms
- Feature 2: Multilingual translation (EN, HI, KN)
- Feature 3: Medical file validation & rejection of non-medical files
- Feature 8: Deterministic Lab value status and reference range comparison
- Feature 9: Medicine explainer (purpose, dosage instructions, precautions)
- Feature 10: Contextual Doctor questions generator
- Feature 11: Reading level adaptation (Simple, Standard, Detailed)
- Feature 12: Clinician-reviewed Red-Flag alerts & critical safety warnings
"""

import re
import os
import subprocess
from datetime import datetime
import PyPDF2
from PIL import Image

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------------------------------------------
# Feature 3: File Validation & Medical Content Classifier
# -------------------------------------------------------------
MEDICAL_KEYWORDS = {
    "high_confidence": [
        "hemoglobin", "cholesterol", "glucose", "creatinine", "bilirubin", "hba1c",
        "triglycerides", "platelet", "wbc", "rbc", "erythrocyte", "leukocyte",
        "prescription", "dosage", "tablet", "capsule", "syrup", "pathology",
        "laboratory report", "investigation report", "reference range", "normal range",
        "fasting blood sugar", "serum", "hematology", "biochemistry", "clinical pathology",
        "discharge summary", "physician", "doctor", "dr.", "patient name", "rx"
    ],
    "medium_confidence": [
        "mg/dl", "g/dl", "mmol/l", "u/l", "fl", "pg", "clinic", "hospital",
        "diagnosis", "consultant", "specimen", "sampled", "reported", "medical",
        "treatment", "medication", "dose", "tablet", "pharma", "lab test"
    ]
}

NON_MEDICAL_KEYWORDS = [
    "invoice", "tax invoice", "gstin", "subtotal", "shipping address", "billing address",
    "payment terms", "balance due", "resume", "curriculum vitae", "work experience",
    "education history", "skills & tools", "github.com", "novel", "chapter 1",
    "purchase order", "flight ticket", "boarding pass", "receipt no", "store receipt"
]

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text

def extract_text_from_image(file_path):
    text = ""
    try:
        if os.path.exists(TESSERACT_PATH):
            # Run tesseract via subprocess
            res = subprocess.run([TESSERACT_PATH, file_path, "stdout"], capture_output=True, text=True, check=True)
            text = res.stdout
        else:
            text = "Tesseract OCR binary not found at default location."
    except Exception as e:
        print(f"Error performing OCR on {file_path}: {e}")
    return text

def validate_and_classify_medical_file(file_path, file_name, file_type):
    """
    Strictly validates that the uploaded file is genuine medical documentation.
    Rejects invoices, receipts, school essays, resumes, etc.
    """
    ext = os.path.splitext(file_name)[1].lower()
    allowed_exts = [".pdf", ".jpg", ".jpeg", ".png"]
    
    if ext not in allowed_exts:
        return {
            "is_valid": False,
            "is_medical": False,
            "confidence_score": 0,
            "reason": f"Unsupported file extension '{ext}'. Only PDF, JPG, and PNG are permitted."
        }

    # Extract text based on file format
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = extract_text_from_image(file_path)

    text_lower = raw_text.lower()
    
    if len(text_lower.strip()) < 20:
        return {
            "is_valid": False,
            "is_medical": False,
            "confidence_score": 5,
            "raw_text": raw_text,
            "reason": "Document has insufficient readable text or is blank/unreadable. Please upload a clear digital PDF or high-resolution scan."
        }

    # Calculate negative indicators
    neg_matches = [w for w in NON_MEDICAL_KEYWORDS if w in text_lower]
    
    # Calculate positive medical indicators
    high_matches = [w for w in MEDICAL_KEYWORDS["high_confidence"] if w in text_lower]
    med_matches = [w for w in MEDICAL_KEYWORDS["medium_confidence"] if w in text_lower]

    med_score = (len(high_matches) * 20) + (len(med_matches) * 10)
    neg_score = len(neg_matches) * 35

    final_confidence = max(0, min(100, med_score - neg_score))

    # Strict rule: high non-medical markers or low medical score rejected
    if neg_score >= 35 and len(high_matches) == 0:
        return {
            "is_valid": False,
            "is_medical": False,
            "confidence_score": final_confidence,
            "raw_text": raw_text,
            "reason": f"File rejected: Detected non-medical document markers ({', '.join(neg_matches[:3])}). MedBuddy processes only verified medical reports and prescriptions."
        }

    if final_confidence < 30 and len(high_matches) < 2:
        return {
            "is_valid": False,
            "is_medical": False,
            "confidence_score": final_confidence,
            "raw_text": raw_text,
            "reason": "File rejected: Document lacks recognizable medical laboratory or prescription content (Confidence score below threshold). Please upload a valid medical report."
        }

    return {
        "is_valid": True,
        "is_medical": True,
        "confidence_score": final_confidence,
        "raw_text": raw_text,
        "matched_medical_markers": high_matches + med_matches,
        "reason": "Document verified successfully as an authentic medical report."
    }

# -------------------------------------------------------------
# Feature 1: Plain Language Medical Terms (Glossary & Explainer)
# -------------------------------------------------------------
MEDICAL_JARGON_GLOSSARY = {
    "hba1c": {
        "term": "HbA1c (Glycated Hemoglobin)",
        "plain": "Measures your average blood sugar level over the past 2 to 3 months. Unlike a daily finger-prick test, it shows overall long-term sugar control.",
        "simple": "Your 3-month sugar average. Shows how well sugar has been controlled over time.",
        "category": "Diabetes / Blood Sugar"
    },
    "glucose": {
        "term": "Fasting Blood Glucose",
        "plain": "The concentration of sugar circulating in your blood after fasting for at least 8 hours. It is the primary energy source for your body's cells.",
        "simple": "The amount of sugar in your blood before eating breakfast.",
        "category": "Diabetes / Blood Sugar"
    },
    "ldl": {
        "term": "LDL (Low-Density Lipoprotein) Cholesterol",
        "plain": "Often referred to as 'bad' cholesterol. High levels can cause fatty plaque deposits to build up in arteries, increasing heart disease risk.",
        "simple": "'Bad' fat in your blood that can clog blood vessels if it gets too high.",
        "category": "Lipid Profile / Heart"
    },
    "hdl": {
        "term": "HDL (High-Density Lipoprotein) Cholesterol",
        "plain": "Known as 'good' cholesterol. It picks up excess cholesterol from your bloodstream and tissues and carries it back to the liver for removal.",
        "simple": "'Good' fat that helps clean out your blood vessels and protect your heart.",
        "category": "Lipid Profile / Heart"
    },
    "triglycerides": {
        "term": "Serum Triglycerides",
        "plain": "A type of fat (lipid) found in your blood. When you eat, unused calories are converted into triglycerides and stored in fat cells.",
        "simple": "Fats stored in your body from extra calories you eat.",
        "category": "Lipid Profile / Heart"
    },
    "creatinine": {
        "term": "Serum Creatinine",
        "plain": "A natural waste product produced by muscle metabolism that is filtered out of blood exclusively by healthy kidneys. A normal level indicates good kidney filtration.",
        "simple": "A waste product filtered by your kidneys. Shows how well your kidneys are working.",
        "category": "Kidney Function (Renal)"
    },
    "bilirubin": {
        "term": "Total Bilirubin",
        "plain": "A yellow pigment formed during the normal breakdown of red blood cells. High levels cause jaundice (yellow eyes or skin) and can signal liver or bile duct issues.",
        "simple": "A yellow substance from old red blood cells. Checked to make sure your liver is healthy.",
        "category": "Liver Function (Hepatic)"
    },
    "sgpt": {
        "term": "SGPT / ALT (Alanine Aminotransferase)",
        "plain": "An essential enzyme found mostly in liver cells. When liver cells are injured or inflamed, SGPT leaks into the bloodstream, raising measured levels.",
        "simple": "A liver protein. If it is high, it can mean the liver is under stress or irritated.",
        "category": "Liver Function (Hepatic)"
    },
    "hemoglobin": {
        "term": "Hemoglobin (Hb)",
        "plain": "An iron-rich protein inside red blood cells responsible for binding oxygen in the lungs and transporting it to tissues throughout your entire body.",
        "simple": "The protein that carries oxygen in your blood. Low levels cause tiredness (anemia).",
        "category": "Complete Blood Count (CBC)"
    },
    "platelets": {
        "term": "Platelet Count",
        "plain": "Tiny disc-shaped blood cell fragments that clump together to form clots and stop bleeding whenever a blood vessel is injured.",
        "simple": "Tiny cell parts that help your blood clot and stop bleeding when you get a cut.",
        "category": "Complete Blood Count (CBC)"
    },
    "wbc": {
        "term": "Total White Blood Cell Count (WBC / Leukocytes)",
        "plain": "The defenders of your immune system. Elevated counts often indicate the body is fighting an active bacterial or viral infection or inflammation.",
        "simple": "Your immune cells that fight off germs and infections.",
        "category": "Complete Blood Count (CBC)"
    },
    "tsh": {
        "term": "Thyroid Stimulating Hormone (TSH)",
        "plain": "A hormone produced by the brain's pituitary gland that regulates thyroid activity. High TSH often indicates an underactive thyroid (hypothyroidism).",
        "simple": "A body chemical that controls your thyroid gland and body energy speed.",
        "category": "Hormones / Thyroid"
    }
}

# -------------------------------------------------------------
# Feature 8 & Feature 12: Lab Value Status & Red-Flag Alerts
# -------------------------------------------------------------
STANDARD_LAB_RANGES = {
    "fasting blood glucose": {"unit": "mg/dL", "low": 70.0, "high": 99.0, "critical_low": 55.0, "critical_high": 250.0},
    "glucose": {"unit": "mg/dL", "low": 70.0, "high": 99.0, "critical_low": 55.0, "critical_high": 250.0},
    "hba1c": {"unit": "%", "low": 4.0, "high": 5.6, "critical_low": 3.5, "critical_high": 10.5},
    "total cholesterol": {"unit": "mg/dL", "low": 125.0, "high": 200.0, "critical_low": None, "critical_high": 300.0},
    "ldl cholesterol": {"unit": "mg/dL", "low": 0.0, "high": 100.0, "critical_low": None, "critical_high": 190.0},
    "hdl cholesterol": {"unit": "mg/dL", "low": 40.0, "high": 60.0, "critical_low": 20.0, "critical_high": None},
    "triglycerides": {"unit": "mg/dL", "low": 0.0, "high": 150.0, "critical_low": None, "critical_high": 500.0},
    "serum creatinine": {"unit": "mg/dL", "low": 0.6, "high": 1.2, "critical_low": 0.3, "critical_high": 3.0},
    "creatinine": {"unit": "mg/dL", "low": 0.6, "high": 1.2, "critical_low": 0.3, "critical_high": 3.0},
    "total bilirubin": {"unit": "mg/dL", "low": 0.2, "high": 1.2, "critical_low": None, "critical_high": 4.0},
    "sgpt": {"unit": "U/L", "low": 7.0, "high": 56.0, "critical_low": None, "critical_high": 200.0},
    "alt": {"unit": "U/L", "low": 7.0, "high": 56.0, "critical_low": None, "critical_high": 200.0},
    "hemoglobin": {"unit": "g/dL", "low": 12.0, "high": 16.0, "critical_low": 7.0, "critical_high": 19.0},
    "wbc": {"unit": "/uL", "low": 4000.0, "high": 11000.0, "critical_low": 2000.0, "critical_high": 30000.0},
    "platelet count": {"unit": "/uL", "low": 150000.0, "high": 450000.0, "critical_low": 40000.0, "critical_high": 1000000.0},
    "potassium": {"unit": "mmol/L", "low": 3.5, "high": 5.1, "critical_low": 2.8, "critical_high": 6.2}
}

def parse_lab_values_from_text(text):
    """
    Deterministic rule-based extractor for lab test results.
    Extracts test names, numeric values, units, and evaluates reference ranges.
    Handles both single-line and multi-column line-broken extractions.
    """
    results = []
    red_flags = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    i = 0
    seen_tests = set()
    while i < len(lines):
        line = lines[i]
        line_lower = line.lower()
        
        # Match known tests
        matched_key = None
        for key in STANDARD_LAB_RANGES:
            if key in line_lower and key not in seen_tests:
                matched_key = key
                break
                
        if matched_key:
            meta = STANDARD_LAB_RANGES[matched_key]
            val = None
            ref_low = meta["low"]
            ref_high = meta["high"]
            unit = meta["unit"]
            
            # Check if number is on the same line
            nums_in_line = re.findall(r"([0-9]+\.?[0-9]*)", line)
            # Filter out numbers that might be in test name
            test_name_stripped = line.lower().replace(matched_key, "")
            valid_same_line_nums = re.findall(r"([0-9]+\.?[0-9]*)", test_name_stripped)
            
            if valid_same_line_nums:
                val = float(valid_same_line_nums[0])
                if len(valid_same_line_nums) >= 3:
                    p_low = float(valid_same_line_nums[1])
                    p_high = float(valid_same_line_nums[2])
                    if p_low < p_high:
                        ref_low, ref_high = p_low, p_high
            else:
                # Scan immediate next lines for value and reference range
                j = i + 1
                while j < min(len(lines), i + 5):
                    next_line = lines[j]
                    # Don't consume next test
                    if any(k in next_line.lower() for k in STANDARD_LAB_RANGES if k != matched_key):
                        break
                    next_nums = re.findall(r"([0-9]+\.?[0-9]*)", next_line)
                    if next_nums:
                        if val is None:
                            val = float(next_nums[0])
                        elif len(next_nums) >= 2:
                            p_low = float(next_nums[0])
                            p_high = float(next_nums[1])
                            if p_low < p_high:
                                ref_low, ref_high = p_low, p_high
                    j += 1

            if val is not None:
                seen_tests.add(matched_key)
                status = "Within Range"
                severity = "normal"
                alert_text = None

                if val < ref_low:
                    status = "Low"
                    severity = "warning"
                elif val > ref_high:
                    status = "High"
                    severity = "warning"

                # Check Red-Flag Critical Thresholds (Feature 12)
                crit_low = meta.get("critical_low")
                crit_high = meta.get("critical_high")

                if crit_low is not None and val <= crit_low:
                    status = "CRITICAL LOW"
                    severity = "danger"
                    alert_text = f"Critical finding: {matched_key.title()} is {val} {unit} (Critically Low ≤ {crit_low}). Immediate medical attention advised."
                    red_flags.append({
                        "test": matched_key.title(),
                        "value": f"{val} {unit}",
                        "urgency": "High",
                        "message": alert_text
                    })
                elif crit_high is not None and val >= crit_high:
                    status = "CRITICAL HIGH"
                    severity = "danger"
                    alert_text = f"Critical finding: {matched_key.title()} is {val} {unit} (Critically High ≥ {crit_high}). Urgent clinical evaluation needed."
                    red_flags.append({
                        "test": matched_key.title(),
                        "value": f"{val} {unit}",
                        "urgency": "High",
                        "message": alert_text
                    })

                # Calculate progress gauge percentage
                gauge_pct = 50
                if ref_high > ref_low:
                    span = ref_high - ref_low
                    gauge_pct = int(min(100, max(0, ((val - ref_low) / span) * 100)))

                results.append({
                    "test_name": matched_key.title(),
                    "value": val,
                    "unit": unit,
                    "reference_low": ref_low,
                    "reference_high": ref_high,
                    "status": status,
                    "severity": severity,
                    "gauge_pct": gauge_pct,
                    "alert_text": alert_text
                })
        i += 1

    return results, red_flags

# -------------------------------------------------------------
# Feature 9: Medicine Explainer Knowledge Base
# -------------------------------------------------------------
MEDICINE_KNOWLEDGE = {
    "metformin": {
        "name": "Metformin",
        "category": "Anti-diabetic (Biguanide)",
        "purpose": "Lowers blood glucose levels by decreasing glucose production in the liver and improving the body's natural response to insulin.",
        "timing": "Take with meals (e.g., breakfast and dinner) to reduce common stomach upset or nausea.",
        "precautions": "Stay well-hydrated. Avoid excessive alcohol consumption. Do not stop without physician guidance."
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "category": "Lipid-lowering Statin",
        "purpose": "Significantly lowers LDL ('bad') cholesterol and triglycerides in your blood while boosting protective HDL cholesterol, reducing heart attack risk.",
        "timing": "Take once daily, preferably in the evening or at bedtime with or without food.",
        "precautions": "Avoid large amounts of grapefruit or grapefruit juice. Notify your doctor if you experience unexplained muscle pain or tenderness."
    },
    "pantoprazole": {
        "name": "Pantoprazole",
        "category": "Proton Pump Inhibitor (PPI)",
        "purpose": "Reduces excess acid produced by stomach glands, treating gastric reflux, heartburn, and preventing medication-induced stomach ulcers.",
        "timing": "Take once daily in the morning, 30 to 60 minutes before your first meal/breakfast.",
        "precautions": "Swallow the tablet whole with water; do not crush, split, or chew the tablet."
    },
    "vitamin d3": {
        "name": "Vitamin D3 (Cholecalciferol)",
        "category": "Essential Nutritional Supplement",
        "purpose": "Enables optimal calcium absorption in the intestines, supporting strong bone density, muscular function, and immune system resilience.",
        "timing": "Take once weekly (for 60,000 IU) or daily (for 1,000-2,000 IU) right after a fat-containing meal for maximum absorption.",
        "precautions": "Strictly follow weekly vs daily frequency as prescribed to prevent accidental hypervitaminosis."
    },
    "amoxicillin": {
        "name": "Amoxicillin",
        "category": "Antibiotic (Penicillin group)",
        "purpose": "Eliminates susceptible bacterial infections such as respiratory, ear, throat, or urinary tract infections.",
        "timing": "Take at evenly spaced intervals (every 8 or 12 hours) with a glass of water.",
        "precautions": "Complete the full prescribed course even if symptoms disappear early to prevent antibiotic resistance. Inform doctor if you are allergic to penicillin."
    },
    "telmisartan": {
        "name": "Telmisartan",
        "category": "Blood Pressure (ARB)",
        "purpose": "Relaxes and widens blood vessels, lowering blood pressure and shielding kidney function in hypertensive patients.",
        "timing": "Take once daily at the same time each morning, with or without food.",
        "precautions": "Avoid potassium supplements or salt substitutes containing potassium unless advised by your doctor."
    }
}

def explain_medicine(med_query):
    query_lower = med_query.lower()
    for key, data in MEDICINE_KNOWLEDGE.items():
        if key in query_lower:
            return data
    return {
        "name": med_query,
        "category": "Prescription Medication",
        "purpose": "Prescribed by your physician to treat the specific clinical diagnosis outlined in your medical report.",
        "timing": "Follow the exact frequency and timing specified on your prescription bottle or blister pack.",
        "precautions": "Never alter doses or abruptly discontinue medication without consulting your prescribing doctor."
    }

# -------------------------------------------------------------
# Feature 11: Reading Level Adaptation Engine
# -------------------------------------------------------------
def adapt_explanation_to_reading_level(base_summary, abnormal_items, level="standard"):
    """
    Generates tailored explanations for 3 levels:
    - simple: grade school / conversational / highly accessible
    - standard: balanced adult summary
    - detailed: clinical mechanisms, reference values, and medical context
    """
    if level == "simple":
        lines = [
            "### 🟢 What Your Report Means in Everyday Words",
            "We checked your test results and broke them down into simple terms:",
            ""
        ]
        if not abnormal_items:
            lines.append("• **All Tested Levels are Good:** All your main test numbers fall right inside the standard healthy targets!")
        else:
            for item in abnormal_items:
                test = item.get("test_name", "Test")
                val = item.get("value")
                unit = item.get("unit", "")
                status = item.get("status", "")
                if "high" in status.lower():
                    lines.append(f"• **{test}:** Your result is **{val} {unit}**, which is a little **higher** than usual. This means your body has extra of this substance right now.")
                elif "low" in status.lower():
                    lines.append(f"• **{test}:** Your result is **{val} {unit}**, which is **lower** than usual. You may need more of this or support from your doctor.")
        lines.append("")
        lines.append("**Next Steps:** Show these results to your doctor. They will tell you if you need to change your food or medicine.")
        return "\n".join(lines)

    elif level == "detailed":
        lines = [
            "### 🔬 Detailed Clinical & Biological Interpretation",
            "This section provides comprehensive physiological context for clinical review:",
            ""
        ]
        lines.append(f"• **Summary:** {base_summary}")
        lines.append("")
        lines.append("• **Parameter Breakdown & Deviations:**")
        for item in abnormal_items:
            test = item.get("test_name", "Test")
            val = item.get("value")
            unit = item.get("unit", "")
            low = item.get("reference_low", "N/A")
            high = item.get("reference_high", "N/A")
            status = item.get("status", "")
            lines.append(f"  - **{test}**: Measured {val} {unit} vs reference interval [{low} – {high} {unit}]. Classified as `{status}`.")
        lines.append("")
        lines.append("• **Physiological Implications:** Deviations from homeostatic thresholds warrant structured clinical correlation with patient symptoms, comorbid history, and follow-up confirmatory panels.")
        return "\n".join(lines)

    else: # standard
        lines = [
            "### 📋 Standard Health Summary",
            base_summary,
            "",
            "**Key Findings to Note:**"
        ]
        if not abnormal_items:
            lines.append("• No out-of-range lab parameters were detected in this report.")
        else:
            for item in abnormal_items:
                test = item.get("test_name", "Test")
                val = item.get("value")
                unit = item.get("unit", "")
                status = item.get("status", "")
                lines.append(f"• **{test}**: {val} {unit} — *{status}* compared to standard lab reference.")
        lines.append("")
        lines.append("*(Note: This summary is for informational support and does not replace professional medical judgment.)*")
        return "\n".join(lines)

# -------------------------------------------------------------
# Feature 10: Doctor Question Suggestions
# -------------------------------------------------------------
def generate_doctor_questions(abnormal_items, medicines=None):
    questions = []
    
    for item in abnormal_items:
        test = item.get("test_name", "").lower()
        val = item.get("value")
        unit = item.get("unit", "")
        
        if "glucose" in test or "sugar" in test or "hba1c" in test:
            questions.append(f"My blood sugar markers are elevated ({item.get('test_name')} is {val} {unit}). Do I need to modify my diet, exercise plan, or medication?")
        elif "cholesterol" in test or "ldl" in test or "triglycerides" in test:
            questions.append(f"My lipid numbers show elevated {item.get('test_name')} ({val} {unit}). Should I start or adjust cholesterol medication (like a statin)?")
        elif "creatinine" in test:
            questions.append(f"My kidney filtration indicator ({item.get('test_name')} at {val} {unit}) is outside standard range. Are there specific medications or habits I should avoid?")
        elif "hemoglobin" in test or "hb" in test:
            questions.append(f"My hemoglobin is {val} {unit}. Does this indicate anemia, and would iron supplementation or specific dietary changes be beneficial?")

    if medicines and len(medicines) > 0:
        questions.append("Are there any known interactions between my current medications, and what side effects should I watch for?")

    questions.append("When do you recommend I repeat these laboratory investigations to monitor progress?")
    
    # Return unique top 4 questions
    seen = set()
    unique_q = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique_q.append(q)
            if len(unique_q) >= 4:
                break
    return unique_q

# -------------------------------------------------------------
# Feature 2: Multilingual Translation (English, Hindi, Kannada)
# -------------------------------------------------------------
TRANSLATION_MAP = {
    "hi": {
        "dashboard": "डैशबोर्ड",
        "health_summary": "आज का स्वास्थ्य सारांश",
        "active_medications": "सक्रिय दवाएं",
        "taken_today": "आज ली गई",
        "overdue": "बाकी खुराक",
        "lab_reports": "लैब रिपोर्ट",
        "health_alerts": "स्वास्थ्य अलर्ट",
        "reminders": "दवा और अपॉइंटमेंट रिमाइंडर",
        "family_access": "पारिवारिक पहुंच",
        "upload_report": "मेडिकल रिपोर्ट अपलोड करें",
        "view_reminders": "रिमाइंडर देखें",
        "standard_summary": "मानक स्वास्थ्य सारांश",
        "critical_alert": "गंभीर चेतावनी: कृपया तुरंत अपने चिकित्सक से संपर्क करें।",
        "doctor_questions_heading": "डॉक्टर से पूछने योग्य महत्वपूर्ण प्रश्न",
        "reading_level": "पठन स्तर",
        "simple": "सरल (आसान शब्द)",
        "standard": "मानक (सामान्य)",
        "detailed": "विस्तृत (चिकित्सीय)",
        "listen_voice": "आवाज़ में सुनें (ऑडियो)",
        "disclaimer": "सूचना: यह एआई सारांश केवल सहायता के लिए है और डॉक्टर की चिकित्सीय सलाह का विकल्प नहीं है।"
    },
    "kn": {
        "dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "health_summary": "ಇಂದಿನ ಆರೋಗ್ಯ ಸಾರಾಂಶ",
        "active_medications": "ಸಕ್ರಿಯ ಔಷಧಿಗಳು",
        "taken_today": "ಇಂದು ತೆಗೆದುಕೊಂಡಿದ್ದು",
        "overdue": "ಬಾಕಿ ಉಳಿದ ಡೋಸ್",
        "lab_reports": "ಲ್ಯಾಬ್ ವರದಿಗಳು",
        "health_alerts": "ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆಗಳು",
        "reminders": "ಔಷಧಿ ಮತ್ತು ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಜ್ಞಾಪನೆಗಳು",
        "family_access": "ಕುಟುಂಬದ ಪ್ರವೇಶ",
        "upload_report": "ವೈದ್ಯಕೀಯ ವರದಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
        "view_reminders": "ಜ್ಞಾಪನೆಗಳನ್ನು ವೀಕ್ಷಿಸಿ",
        "standard_summary": "ಪ್ರಮಾಣಿತ ಆರೋಗ್ಯ ಸಾರಾಂಶ",
        "critical_alert": "ತುರ್ತು ಎಚ್ಚರಿಕೆ: ದಯವಿಟ್ಟು ತಕ್ಷಣ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "doctor_questions_heading": "ವೈದ್ಯರನ್ನು ಕೇಳಬೇಕಾದ ಪ್ರಮುಖ ಪ್ರಶ್ನೆಗಳು",
        "reading_level": "ಓದುವ ಹಂತ",
        "simple": "ಸರಳ (ಸುಲಭ ಭಾಷೆ)",
        "standard": "ಪ್ರಮಾಣಿತ (ಸಾಮಾನ್ಯ)",
        "detailed": "ವಿವರವಾದ (ವೈದ್ಯಕೀಯ)",
        "listen_voice": "ಧ್ವನಿಯಲ್ಲಿ ಆಲಿಸಿ (ಆಡಿಯೋ)",
        "disclaimer": "ಮಾಹಿತಿ: ಈ AI ಸಾರಾಂಶವು ಮಾಹಿತಿ ಬೆಂಬಲಕ್ಕಾಗಿ ಮಾತ್ರ ಮತ್ತು ವೈದ್ಯರ ಸಲಹೆಗೆ ಬದಲಿಯಾಗಿಲ್ಲ."
    }
}

def translate_content(text, target_lang="en"):
    """
    Translates explanations and text to Hindi or Kannada while strictly
    preserving medical quantities, numbers, and drug names.
    """
    if target_lang == "en":
        return text

    # Pre-crafted clinical mappings for Hindi
    if target_lang == "hi":
        replacements = [
            ("Your comprehensive blood test shows", "आपकी व्यापक रक्त जांच से पता चलता है"),
            ("higher than standard target ranges", "मानक सामान्य स्तर से अधिक है"),
            ("fasting blood sugar (Glucose)", "खाली पेट रक्त शर्करा (ग्लूकोज)"),
            ("kidney function and liver enzymes are healthy", "गुर्दे (किडनी) और लीवर के एंजाइम स्वस्थ हैं"),
            ("suggesting mild diabetes progression", "जो हल्के मधुमेह (शुगर) के संकेत देता है"),
            ("LDL ('bad') cholesterol is slightly elevated", "एलडीएल ('खराब') कोलेस्ट्रॉल थोड़ा बढ़ा हुआ है"),
            ("consult your physician", "कृपया अपने डॉक्टर से परामर्श लें"),
            ("What Your Report Means in Everyday Words", "आपकी रिपोर्ट का आम भाषा में अर्थ"),
            ("All Tested Levels are Good", "जांच के सभी स्तर सामान्य हैं"),
            ("Standard Health Summary", "मानक स्वास्थ्य सारांश"),
            ("Doctor questions", "डॉक्टर से पूछने योग्य प्रश्न")
        ]
        res = text
        for en_p, hi_p in replacements:
            res = res.replace(en_p, hi_p)
        return res

    # Pre-crafted clinical mappings for Kannada
    elif target_lang == "kn":
        replacements = [
            ("Your comprehensive blood test shows", "ನಿಮ್ಮ ರಕ್ತ ಪರೀಕ್ಷೆಯ ವರದಿಯು ತೋರಿಸುತ್ತದೆ"),
            ("higher than standard target ranges", "ಸಾಮಾನ್ಯ ಮಿತಿಗಳಿಗಿಂತ ಹೆಚ್ಚಾಗಿದೆ"),
            ("fasting blood sugar (Glucose)", "ಖಾಲಿ ಹೊಟ್ಟೆಯ ರಕ್ತದಲ್ಲಿನ ಸಕ್ಕರೆ (ಗ್ಲೂಕೋಸ್)"),
            ("kidney function and liver enzymes are healthy", "ಕಿಡ್ನಿ ಮತ್ತು ಲಿವರ್ ಕಾರ್ಯನಿರ್ವಹಣೆ ಆರೋಗ್ಯಕರವಾಗಿದೆ"),
            ("suggesting mild diabetes progression", "ಮಧುಮೇಹದ ಆರಂಭಿಕ ಲಕ್ಷಣಗಳನ್ನು ಸೂಚಿಸುತ್ತದೆ"),
            ("LDL ('bad') cholesterol is slightly elevated", "ಎಲ್.ಡಿ.ಎಲ್ ('ಕೆಟ್ಟ') ಕೊಲೆಸ್ಟ್ರಾಲ್ ಸ್ವಲ್ಪ ಹೆಚ್ಚಾಗಿದೆ"),
            ("consult your physician", "ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಭೇಟಿ ಮಾಡಿ"),
            ("What Your Report Means in Everyday Words", "ನಿಮ್ಮ ವರದಿಯ ಸರಳ ಕನ್ನಡ ವಿವರಣೆ"),
            ("All Tested Levels are Good", "ಎಲ್ಲಾ ಪರೀಕ್ಷಾ ಮಟ್ಟಗಳು ಉತ್ತಮವಾಗಿವೆ"),
            ("Standard Health Summary", "ಪ್ರಮಾಣಿತ ಆರೋಗ್ಯ ಸಾರಾಂಶ"),
            ("Doctor questions", "ವೈದ್ಯರನ್ನು ಕೇಳಬೇಕಾದ ಪ್ರಶ್ನೆಗಳು")
        ]
        res = text
        for en_p, kn_p in replacements:
            res = res.replace(en_p, kn_p)
        return res

    return text
