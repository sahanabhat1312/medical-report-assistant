"""
Generate sample PDF and Image files for testing MedBuddy MVP.
Generates:
1. sample_cbc_lab_report.pdf (Standard medical report)
2. sample_critical_redflag_report.pdf (Critical alert test)
3. sample_non_medical_invoice.pdf (To demonstrate strict rejection of non-medical files)
4. sample_prescription.png (Image to test Tesseract OCR)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(SAMPLE_DIR, exist_ok=True)

def create_lab_report_pdf():
    pdf_path = os.path.join(SAMPLE_DIR, "sample_cbc_lab_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.drawString(50, height - 50, "METROPOLIS CLINICAL PATHOLOGY LABORATORY")
    
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(50, height - 65, "Accredited Diagnostic Center | Reg No: LAB-2026-9812 | Contact: +91 80 2345 6789")
    c.line(50, height - 72, width - 50, height - 72)

    # Patient info
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 95, "Patient Name:")
    c.setFont("Helvetica", 10)
    c.drawString(130, height - 95, "Kashish Sharma")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, height - 95, "Age / Gender:")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 95, "34 Y / Female")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 110, "Referred By:")
    c.setFont("Helvetica", 10)
    c.drawString(130, height - 110, "Dr. Arvind Kumar, MD")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, height - 110, "Report Date:")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 110, "10-Nov-2026")

    c.line(50, height - 120, width - 50, height - 120)

    # Table Header
    y = height - 145
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.drawString(50, y, "INVESTIGATION (TEST NAME)")
    c.drawString(240, y, "RESULT")
    c.drawString(320, y, "UNITS")
    c.drawString(400, y, "REFERENCE RANGE")
    c.line(50, y - 5, width - 50, y - 5)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    rows = [
        ("Fasting Blood Glucose", "142", "mg/dL", "70 - 99"),
        ("HbA1c", "7.4", "%", "4.0 - 5.6"),
        ("Total Cholesterol", "228", "mg/dL", "125 - 200"),
        ("LDL Cholesterol", "148", "mg/dL", "0 - 100"),
        ("HDL Cholesterol", "46", "mg/dL", "40 - 60"),
        ("Triglycerides", "175", "mg/dL", "0 - 150"),
        ("Serum Creatinine", "0.85", "mg/dL", "0.6 - 1.2"),
        ("Total Bilirubin", "0.90", "mg/dL", "0.2 - 1.2"),
        ("Hemoglobin", "13.2", "g/dL", "12.0 - 16.0")
    ]

    for item in rows:
        y -= 25
        c.drawString(50, y, item[0])
        c.drawString(240, y, item[1])
        c.drawString(320, y, item[2])
        c.drawString(400, y, item[3])

    # Footer
    c.line(50, 100, width - 50, 100)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 85, "Verified by: Dr. S. Rao, Chief Pathologist (MD Pathology) | End of Report.")
    c.save()
    print("Created sample_cbc_lab_report.pdf")

def create_critical_alert_pdf():
    pdf_path = os.path.join(SAMPLE_DIR, "sample_critical_redflag_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#b91c1c"))
    c.drawString(50, height - 50, "EMERGENCY CLINICAL BIOCHEMISTRY REPORT")
    
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(50, height - 65, "Urgent Care Diagnostic Center | Patient ID: URG-9901")
    c.line(50, height - 72, width - 50, height - 72)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 95, "Patient Name: Kashish Sharma | Age: 34 Y | Date: 12-Nov-2026")
    c.line(50, height - 105, width - 50, height - 105)

    y = height - 130
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#b91c1c"))
    c.drawString(50, y, "CRITICAL LAB INVESTIGATIONS")
    c.drawString(260, y, "RESULT")
    c.drawString(340, y, "UNITS")
    c.drawString(420, y, "REFERENCE")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    rows = [
        ("Fasting Blood Glucose", "285", "mg/dL", "70 - 99"), # CRITICAL HIGH > 250
        ("Potassium", "6.4", "mmol/L", "3.5 - 5.1"),        # CRITICAL HIGH > 6.2
        ("Hemoglobin", "6.8", "g/dL", "12.0 - 16.0"),        # CRITICAL LOW < 7.0
        ("Serum Creatinine", "3.2", "mg/dL", "0.6 - 1.2")     # CRITICAL HIGH > 3.0
    ]

    for item in rows:
        y -= 25
        c.drawString(50, y, item[0])
        c.drawString(260, y, item[1])
        c.drawString(340, y, item[2])
        c.drawString(420, y, item[3])

    c.line(50, 100, width - 50, 100)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, 85, "RED FLAG NOTICE: Critical values telephoned to attending physician.")
    c.save()
    print("Created sample_critical_redflag_report.pdf")

def create_non_medical_invoice_pdf():
    pdf_path = os.path.join(SAMPLE_DIR, "sample_non_medical_invoice.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(50, height - 50, "RETAIL STORE TAX INVOICE")
    
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 65, "GSTIN: 29AAAAA0000A1Z5 | Invoice No: INV-2026-8871")
    c.line(50, height - 72, width - 50, height - 72)

    c.drawString(50, height - 95, "Billing Address: Tech Park, Indiranagar, Bengaluru")
    c.drawString(50, height - 110, "Shipping Method: Standard Courier Express")
    c.line(50, height - 120, width - 50, height - 120)

    y = height - 145
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Item Description")
    c.drawString(300, y, "Qty")
    c.drawString(380, y, "Unit Price")
    c.drawString(460, y, "Subtotal")

    c.setFont("Helvetica", 10)
    rows = [
        ("Wireless Mechanical Keyboard", "1", "$85.00", "$85.00"),
        ("USB-C Fast Charging Hub", "2", "$25.00", "$50.00"),
        ("Ergonomic Desk Mouse Pad", "1", "$18.00", "$18.00")
    ]
    for r in rows:
        y -= 25
        c.drawString(50, y, r[0])
        c.drawString(300, y, r[1])
        c.drawString(380, y, r[2])
        c.drawString(460, y, r[3])

    y -= 35
    c.setFont("Helvetica-Bold", 10)
    c.drawString(380, y, "Total Balance Due: $153.00")
    c.save()
    print("Created sample_non_medical_invoice.pdf")

def create_prescription_image():
    img_path = os.path.join(SAMPLE_DIR, "sample_prescription.png")
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([(20, 20), (780, 80)], fill="#0f766e")
    draw.text((40, 35), "DR. ARVIND KUMAR, MD - ENDOCRINOLOGIST", fill=(255, 255, 255))
    draw.text((40, 55), "Apollo Health City OPD | Phone: +91 80 4455 6677", fill=(230, 245, 245))

    # Patient info
    draw.text((40, 100), "Patient Name: Kashish Sharma", fill=(0, 0, 0))
    draw.text((400, 100), "Date: 10-Nov-2026", fill=(0, 0, 0))
    draw.text((40, 125), "Diagnosis: Type 2 Diabetes Mellitus & Dyslipidemia", fill=(0, 0, 0))
    draw.line([(40, 150), (760, 150)], fill=(200, 200, 200), width=2)

    # Rx Medications
    draw.text((40, 165), "Rx - Prescribed Medications:", fill="#0f766e")

    meds = [
        "1. Tablet Metformin 500mg - 1 tablet BD with meals (morning and evening)",
        "2. Tablet Atorvastatin 10mg - 1 tablet at bedtime (HS)",
        "3. Capsule Pantoprazole 40mg - 1 cap daily morning before breakfast",
        "4. Vitamin D3 60,000 IU - 1 capsule weekly after lunch"
    ]

    y = 200
    for m in meds:
        draw.text((50, y), m, fill=(20, 20, 20))
        y += 40

    draw.line([(40, 480), (760, 480)], fill=(200, 200, 200), width=1)
    draw.text((40, 500), "Instructions: Maintain low-sugar diet and 30 mins brisk walking.", fill=(80, 80, 80))
    draw.text((40, 525), "Follow-up: 3 months with fasting blood sugar and HbA1c reports.", fill=(80, 80, 80))

    img.save(img_path)
    print("Created sample_prescription.png")

if __name__ == "__main__":
    create_lab_report_pdf()
    create_critical_alert_pdf()
    create_non_medical_invoice_pdf()
    create_prescription_image()
