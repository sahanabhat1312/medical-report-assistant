# MedBuddy — AI-Powered Multilingual Medical Report Assistant (MVP)

A patient-first, privacy-respecting healthcare web application that translates dense, jargon-laden medical documents (lab reports, discharge summaries, prescriptions) into plain, reassuring explanations in English, Hindi, and Kannada.

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+ (Current: Python 3.13)
- Required Python packages: `flask`, `pillow`, `PyPDF2`, `reportlab` (already pre-installed)
- Tesseract OCR (installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### 2. Running the Application
Open PowerShell or your command prompt in this directory:

```powershell
cd C:\Users\Sahana\.gemini\antigravity\scratch\medbuddy-mvp
python app.py
```

Then open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🎯 12 Core Features Implementation Map

| # | Feature | Implementation Details |
|---|---|---|
| **1** | **Plain Language Terms** | Built-in clinical terminology glossary that detects complex terms (e.g. *HbA1c*, *LDL*, *Creatinine*, *Bilirubin*, *Platelets*) and explains them in everyday layperson language. |
| **2** | **Multiple Language** | Multi-language translation support for **English**, **Hindi (हिन्दी)**, and **Kannada (ಕನ್ನಡ)**. Strictly preserves medicine brand names, units, and numeric quantities without mistranslation. |
| **3** | **Restrict to Only Medical Files** | Strict file integrity & content classifier. Checks file MIME/signature, evaluates medical keyword density vs non-medical markers. Safely **rejects** non-medical files (invoices, receipts, resumes, novels) with clear diagnostic feedback. |
| **4** | **Text to Voice** | Built-in voice player using the Web Speech API. Reads the simplified explanation aloud in the selected language with play, pause, and stop audio controls. |
| **5** | **Access to Other Close Members** | Patient-controlled family caregiver consent module. Invite family members, assign permission scopes (`view_all`, `view_reports_only`, `manage_reminders`), and revoke/restore access anytime with immutable audit logging. |
| **6** | **Pop-up Messages & Reminders** | Daily dose reminders and doctor appointment alerts with scheduled times, interactive "Mark as Taken" dose tracking, and browser alert notifications. |
| **7** | **History of the Individual** | Chronological patient timeline archiving previous reports, active prescriptions, lab investigations, and an immutable security audit log. |
| **8** | **Value Status** | Deterministic comparison of extracted lab parameters against printed laboratory reference intervals. Displays numeric value, units, status (`Low`, `Within Range`, `High`), and color-coded visual progress gauge bars. |
| **9** | **Medicine Explainer** | Comprehensive medicine card module explaining the active purpose ("Why it is prescribed"), meal timing ("Take with breakfast/empty stomach"), and safety precautions from verified clinical sources. |
| **10** | **Doctor Questions** | Context-aware generation of 3 to 5 targeted follow-up questions tailored specifically to abnormal report results to help patients prepare for consultations. |
| **11** | **Language & Reading Level** | Dynamic 3-level explanation engine: **Simple** (grade-school level, short everyday sentences), **Standard** (balanced conversational adult explanation), and **Detailed** (in-depth clinical context and biological mechanisms). |
| **12** | **Red-Flag Alerts** | Clinician-reviewed deterministic safety rules flagging critical life-threatening values (e.g. Glucose > 250 mg/dL, Potassium > 6.0 mmol/L, Hemoglobin < 7.0 g/dL) with prominent warning banners and urgent care advisories. |

---

## 🧪 Pre-Generated Test Files

The MVP includes 4 instant test files in `sample_data/` accessible directly via 1-click test buttons in the UI:

1. **`sample_cbc_lab_report.pdf`**: Metropolis Pathology Metabolic Panel (Glucose, HbA1c, Lipids, Creatinine, Bilirubin).
2. **`sample_critical_redflag_report.pdf`**: Emergency Biochem report triggering 4 Critical Red-Flag warnings.
3. **`sample_non_medical_invoice.pdf`**: Retail store invoice with GSTIN & shipping items — specifically triggers Feature 3's strict rejection filter!
4. **`sample_prescription.png`**: Scanned image prescription for OCR extraction with Tesseract.

---

## 🔒 Safety Principle
MedBuddy adheres strictly to the clinical safety principle:
*AI simplifies language; deterministic code enforces lab reference comparisons, red-flag triggers, security, access control, and reminders. Informational support only — never autonomous medical diagnosis.*
