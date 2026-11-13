/**
 * MedBuddy - Client-Side Application Logic
 * Supports all 12 PRD features with real-time reactivity
 */

let currentReportData = null;
let currentReadingLevel = "standard";
let currentLanguage = "en";
let currentSpeechUtterance = null;
let isSpeaking = false;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupUploadDropzone();
  setupLanguageSwitcher();
  loadDashboardData();
  loadMedicines();
  loadFamilyMembers();
  loadAuditLogs();
});

// -------------------------------------------------------------
// Navigation & Tab Switching
// -------------------------------------------------------------
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetTab = item.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-tab") === tabId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update tab pane active state
  document.querySelectorAll(".tab-pane").forEach(pane => {
    if (pane.id === tabId) {
      pane.classList.add("active");
    } else {
      pane.classList.remove("active");
    }
  });

  // Update header title
  const titles = {
    "tab-dashboard": "Dashboard Overview",
    "tab-upload": "Medical Document Validation & Upload",
    "tab-analysis": "AI Plain-Language Analysis",
    "tab-lab-values": "Laboratory Value Status & Reference Ranges",
    "tab-red-flags": "Clinician-Reviewed Red-Flag Alerts",
    "tab-medicines": "Prescribed Medicines Explainer",
    "tab-doctor-q": "Recommended Doctor Questions",
    "tab-reminders": "Dose Schedules & Appointment Reminders",
    "tab-family": "Caregiver Access & Sharing Permissions",
    "tab-profile": "Patient Health Profile & Personal Details",
    "tab-history": "Medical Records History & Audit Trail"
  };
  const titleEl = document.getElementById("page-title");
  if (titleEl && titles[tabId]) {
    titleEl.textContent = titles[tabId];
  }

  if (tabId === "tab-profile") {
    loadProfileData();
  }
}

// -------------------------------------------------------------
// Toast Alerts
// -------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  const icon = type === "error" ? "❌" : type === "success" ? "✅" : "🔔";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// -------------------------------------------------------------
// Dashboard Data Loader
// -------------------------------------------------------------
async function loadDashboardData() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    if (data.status === "success") {
      // Update counters
      document.getElementById("stat-active-meds").textContent = data.metrics.active_medications;
      document.getElementById("stat-taken-today").textContent = data.metrics.taken_today;
      document.getElementById("stat-overdue").textContent = data.metrics.overdue;
      document.getElementById("stat-reports-count").textContent = data.metrics.total_reports;

      // Update patient profile
      document.getElementById("user-display-name").textContent = data.patient.name;
      const initials = data.patient.name.split(" ").map(n => n[0]).join("");
      document.getElementById("avatar-initials").textContent = initials;

      // Render today's doses
      renderDashboardDoses(data.today_doses);

      // Render recent reports
      renderDashboardReports(data.recent_reports);
    }
  } catch (err) {
    console.error("Error loading dashboard data:", err);
  }
}

function renderDashboardDoses(doses) {
  const container = document.getElementById("dashboard-doses-list");
  if (!doses || doses.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No doses scheduled for today.</div>`;
    return;
  }

  container.innerHTML = doses.map(dose => `
    <div class="dose-item ${dose.status === 'taken' ? 'taken' : ''}" id="dose-${dose.reminder_id}">
      <div class="dose-meta">
        <input type="checkbox" class="dose-check" ${dose.status === 'taken' ? 'checked' : ''} onchange="toggleDoseReminder('${dose.reminder_id}')">
        <div>
          <div class="dose-title">${escapeHtml(dose.title)}</div>
          <div class="dose-subtitle">${escapeHtml(dose.subtitle || '')}</div>
        </div>
      </div>
      <span class="dose-time">${escapeHtml(dose.scheduled_time)}</span>
    </div>
  `).join("");

  // Also render in full reminders tab
  const allRemList = document.getElementById("all-reminders-list");
  if (allRemList) {
    allRemList.innerHTML = doses.map(dose => `
      <div class="dose-item ${dose.status === 'taken' ? 'taken' : ''}" style="margin-bottom: 12px; padding: 16px;">
        <div class="dose-meta">
          <input type="checkbox" class="dose-check" ${dose.status === 'taken' ? 'checked' : ''} onchange="toggleDoseReminder('${dose.reminder_id}')">
          <div>
            <div class="dose-title" style="font-size: 15px;">${dose.reminder_type === 'appointment' ? '🩺' : '💊'} ${escapeHtml(dose.title)}</div>
            <div class="dose-subtitle">${escapeHtml(dose.subtitle || '')}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="dose-time">${escapeHtml(dose.scheduled_time)}</span>
          <span class="status-badge ${dose.status === 'taken' ? 'badge-normal' : 'badge-warning'}">${dose.status.toUpperCase()}</span>
        </div>
      </div>
    `).join("");
  }
}

async function toggleDoseReminder(reminderId) {
  try {
    const res = await fetch(`/api/reminders/${reminderId}/toggle`, { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`Dose marked as ${data.new_status}!`, "success");
      loadDashboardData();
    }
  } catch (err) {
    showToast("Failed to update reminder status", "error");
  }
}

function renderDashboardReports(reports) {
  const container = document.getElementById("dashboard-recent-reports");
  const histContainer = document.getElementById("reports-history-list");

  if (!reports || reports.length === 0) {
    const emptyHtml = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No reports uploaded yet.</div>`;
    container.innerHTML = emptyHtml;
    if (histContainer) histContainer.innerHTML = emptyHtml;
    return;
  }

  const html = reports.map(r => `
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 8px;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 20px;">📄</span>
        <div>
          <div style="font-weight: 600; font-size: 13px;">${escapeHtml(r.file_name)}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(r.report_type)} • ${escapeHtml(r.report_date || 'Recent')}</div>
        </div>
      </div>
      <span class="status-badge badge-normal">Analyzed</span>
    </div>
  `).join("");

  container.innerHTML = html;
  if (histContainer) histContainer.innerHTML = html;
}

// -------------------------------------------------------------
// Feature 3: File Upload & Medical Document Validation
// -------------------------------------------------------------
function setupUploadDropzone() {
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "#0f766e";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "#99f6e4";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "#99f6e4";
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });
}

async function handleFileUpload(file) {
  const feedbackEl = document.getElementById("upload-feedback");
  feedbackEl.style.display = "block";
  feedbackEl.className = "alert-box alert-warning";
  feedbackEl.innerHTML = `<span>⏳</span> <div>Validating document authenticity and extracting clinical data...</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/reports/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (res.status === 422 || data.status === "rejected") {
      // Rejection of Non-Medical File (Feature 3)
      feedbackEl.className = "alert-box alert-danger";
      feedbackEl.innerHTML = `
        <span style="font-size: 22px;">🚫</span>
        <div>
          <strong>Document Rejected: Non-Medical File</strong><br>
          ${escapeHtml(data.message)}<br>
          <small style="opacity: 0.85;">Confidence: ${data.confidence_score}%. MedBuddy strictly restricts analysis to verified medical reports and prescriptions.</small>
        </div>
      `;
      showToast("Uploaded file was rejected: Non-medical content detected", "error");
      loadAuditLogs();
      return;
    }

    if (data.status === "success") {
      feedbackEl.className = "alert-box alert-success";
      feedbackEl.innerHTML = `
        <span style="font-size: 22px;">✅</span>
        <div>
          <strong>Medical Document Verified & Analyzed!</strong><br>
          ${escapeHtml(data.file_name)} • Extracted ${data.lab_results.length} laboratory parameters.
        </div>
      `;
      showToast("Medical document validated successfully!", "success");

      populateAnalysisData(data);
      switchTab("tab-analysis");
      loadDashboardData();
      loadAuditLogs();
    }
  } catch (err) {
    feedbackEl.className = "alert-box alert-danger";
    feedbackEl.innerHTML = `<span>❌</span> <div>Error uploading file: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------
// Instant 1-Click Sample Testing
// -------------------------------------------------------------
async function loadSampleReport(sampleType) {
  const feedbackEl = document.getElementById("upload-feedback");
  feedbackEl.style.display = "block";
  feedbackEl.className = "alert-box alert-warning";
  feedbackEl.innerHTML = `<span>⏳</span> <div>Loading test sample: <strong>${sampleType}</strong>...</div>`;

  try {
    const res = await fetch(`/api/reports/sample/${sampleType}`, { method: "POST" });
    const data = await res.json();

    if (res.status === 422 || data.status === "rejected") {
      // Demonstrate strict rejection of non-medical invoice!
      feedbackEl.className = "alert-box alert-danger";
      feedbackEl.innerHTML = `
        <span style="font-size: 22px;">🚫</span>
        <div>
          <strong>Document Rejected: Non-Medical File</strong><br>
          ${escapeHtml(data.message)}<br>
          <small>Verified: Medical File Restriction (Feature 3) successfully blocked invoice from clinical pipeline.</small>
        </div>
      `;
      showToast("Rejected non-medical file as expected!", "info");
      return;
    }

    if (data.status === "success") {
      feedbackEl.className = "alert-box alert-success";
      feedbackEl.innerHTML = `<span>✅</span> <div>Sample loaded successfully: ${escapeHtml(data.file_name)}</div>`;
      showToast("Sample loaded successfully!", "success");

      populateAnalysisData(data);
      switchTab("tab-analysis");
    }
  } catch (err) {
    feedbackEl.className = "alert-box alert-danger";
    feedbackEl.innerHTML = `<span>❌</span> <div>Failed to load sample: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------
// Populate Analysis, Lab Values, Red Flags & Questions
// -------------------------------------------------------------
function populateAnalysisData(data) {
  currentReportData = data;

  // Title
  document.getElementById("analysis-report-title").textContent = data.file_name;
  document.getElementById("analysis-report-date").textContent = `Processed on ${new Date().toLocaleDateString()} • Authentic Medical Record`;

  // Summary
  renderSummaryText(data.summary);

  // Plain-Language Terms (Feature 1)
  renderJargonTerms(data.jargon_explained);

  // Lab Values Status (Feature 8)
  renderLabValuesTable(data.lab_results);

  // Red-Flag Alerts (Feature 12)
  renderRedFlags(data.red_flags);

  // Doctor Questions (Feature 10)
  renderDoctorQuestions(data.doctor_questions);
}

function renderSummaryText(text) {
  const box = document.getElementById("analysis-summary-box");
  box.innerHTML = `
    <div style="font-size: 15px; color: var(--text-main);">${escapeHtml(text)}</div>
    <div style="margin-top: 14px; font-size: 12px; color: var(--text-muted); font-style: italic;">
      ℹ️ This explanation is an informational patient support summary and does not replace medical consultation with a registered clinician.
    </div>
  `;
}

function renderJargonTerms(jargonList) {
  const container = document.getElementById("jargon-container");
  if (!jargonList || jargonList.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No complex medical jargon identified in this report.</div>`;
    return;
  }

  container.innerHTML = jargonList.map(j => `
    <div style="background: #ffffff; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px; box-shadow: var(--shadow-sm);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-weight: 600; font-size: 14px; color: var(--primary);">${escapeHtml(j.term)}</span>
        <span style="font-size: 10px; background: var(--primary-light); color: var(--primary); padding: 2px 6px; border-radius: 10px;">${escapeHtml(j.category || 'Term')}</span>
      </div>
      <div style="font-size: 13px; color: var(--text-main); line-height: 1.4;">${escapeHtml(j.plain)}</div>
    </div>
  `).join("");
}

function renderLabValuesTable(labResults) {
  const tbody = document.getElementById("lab-values-tbody");
  if (!labResults || labResults.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">No structured lab values extracted.</td></tr>`;
    return;
  }

  tbody.innerHTML = labResults.map(r => {
    let badgeClass = "badge-normal";
    let fillClass = "background: var(--success);";

    if (r.status.includes("CRITICAL")) {
      badgeClass = "badge-danger";
      fillClass = "background: var(--danger);";
    } else if (r.status === "High" || r.status === "Low") {
      badgeClass = "badge-warning";
      fillClass = "background: var(--warning);";
    }

    return `
      <tr>
        <td style="font-weight: 600;">${escapeHtml(r.test_name)}</td>
        <td style="font-weight: 700; font-size: 15px;">${r.value} <span style="font-weight: normal; font-size: 12px; color: var(--text-muted);">${escapeHtml(r.unit || '')}</span></td>
        <td style="color: var(--text-muted);">${r.reference_low} – ${r.reference_high} ${escapeHtml(r.unit || '')}</td>
        <td><span class="status-badge ${badgeClass}">${escapeHtml(r.status)}</span></td>
        <td>
          <div class="gauge-bar-wrap" title="${r.gauge_pct}% of reference span">
            <div class="gauge-fill" style="width: ${Math.max(10, Math.min(100, r.gauge_pct))}%; ${fillClass}"></div>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function renderRedFlags(redFlags) {
  const container = document.getElementById("red-flags-container");
  if (!redFlags || redFlags.length === 0) {
    container.innerHTML = `
      <div class="alert-box alert-success">
        <span style="font-size: 22px;">🛡️</span>
        <div>
          <strong>No Urgent Red-Flag Alerts Detected</strong><br>
          All evaluated laboratory parameters are within acceptable non-critical ranges. Routine doctor follow-up is recommended.
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = redFlags.map(rf => `
    <div class="alert-box alert-danger" style="margin-bottom: 12px;">
      <span style="font-size: 24px;">🚨</span>
      <div style="flex: 1;">
        <div style="font-weight: 700; font-size: 15px; margin-bottom: 2px;">Critical Priority Alert: ${escapeHtml(rf.test)} (${escapeHtml(rf.value)})</div>
        <div style="font-size: 13px; line-height: 1.4;">${escapeHtml(rf.message)}</div>
        <div style="margin-top: 8px; font-size: 12px; font-weight: 600; color: #7f1d1d;">
          Immediate Action: Please contact your doctor or visit the nearest clinic promptly. Do not self-medicate.
        </div>
      </div>
    </div>
  `).join("");
}

function renderDoctorQuestions(questions) {
  const container = document.getElementById("doctor-questions-list");
  if (!questions || questions.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">No specific questions generated.</div>`;
    return;
  }

  container.innerHTML = questions.map((q, idx) => `
    <div class="q-card">
      <div style="font-size: 14px; color: var(--text-main); font-weight: 500;">
        <strong style="color: var(--primary); margin-right: 6px;">Q${idx + 1}:</strong> ${escapeHtml(q)}
      </div>
      <button class="btn btn-white btn-sm" onclick="copyText('${escapeQuotes(q)}')">Copy</button>
    </div>
  `).join("");
}

// -------------------------------------------------------------
// Feature 11: Reading Level Adapter (Simple, Standard, Detailed)
// -------------------------------------------------------------
async function setReadingLevel(level) {
  currentReadingLevel = level;
  document.querySelectorAll(".level-btn").forEach(btn => {
    btn.classList.toggle("active", btn.textContent.toLowerCase().includes(level));
  });

  if (!currentReportData) return;

  const abnormal = (currentReportData.lab_results || []).filter(r => r.status !== "Within Range");

  try {
    const res = await fetch("/api/explanations/reading-level", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level: level,
        base_summary: currentReportData.summary,
        abnormal_items: abnormal
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      renderSummaryText(data.adapted_text);
      showToast(`Reading level adjusted to ${level.toUpperCase()}`, "info");
    }
  } catch (err) {
    console.error("Error setting reading level:", err);
  }
}

// -------------------------------------------------------------
// Feature 2: Multilingual Language Switcher (EN, HI, KN)
// -------------------------------------------------------------
function setupLanguageSwitcher() {
  const switcher = document.getElementById("language-switcher");
  switcher.addEventListener("change", async (e) => {
    currentLanguage = e.target.value;
    applyLanguage(currentLanguage);
  });
}

async function applyLanguage(lang) {
  if (!currentReportData) return;

  try {
    const summaryText = document.getElementById("analysis-summary-box").innerText;
    const res = await fetch("/api/explanations/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: currentReportData.summary,
        language: lang
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      renderSummaryText(data.translated_text);
      
      // Update UI labels if available
      if (data.ui_labels) {
        if (data.ui_labels.health_summary) {
          document.getElementById("hero-sub-text").textContent = data.ui_labels.health_summary;
        }
      }

      showToast(`Language switched to ${lang.toUpperCase()}`, "success");
    }
  } catch (err) {
    console.error("Error switching language:", err);
  }
}

// -------------------------------------------------------------
// Feature 4: Text-to-Speech (Voice Narration Player)
// -------------------------------------------------------------
function toggleVoiceNarration() {
  if (!('speechSynthesis' in window)) {
    showToast("Web Speech synthesis is not supported on this browser.", "error");
    return;
  }

  if (isSpeaking) {
    window.speechSynthesis.pause();
    isSpeaking = false;
    document.getElementById("voice-btn-text").textContent = "Resume";
    document.getElementById("voice-btn-icon").textContent = "▶️";
    return;
  }

  if (window.speechSynthesis.paused) {
    window.speechSynthesis.resume();
    isSpeaking = true;
    document.getElementById("voice-btn-text").textContent = "Pause";
    document.getElementById("voice-btn-icon").textContent = "⏸️";
    return;
  }

  // Get text to read
  const summaryBox = document.getElementById("analysis-summary-box");
  const textToRead = summaryBox ? summaryBox.innerText : "No report explanation available to read.";

  window.speechSynthesis.cancel(); // Reset
  currentSpeechUtterance = new SpeechSynthesisUtterance(textToRead);

  // Set language
  if (currentLanguage === "hi") {
    currentSpeechUtterance.lang = "hi-IN";
  } else if (currentLanguage === "kn") {
    currentSpeechUtterance.lang = "kn-IN";
  } else {
    currentSpeechUtterance.lang = "en-US";
  }

  currentSpeechUtterance.rate = 0.95; // comfortable speaking pace

  currentSpeechUtterance.onend = () => {
    isSpeaking = false;
    document.getElementById("voice-btn-text").textContent = "Listen Aloud";
    document.getElementById("voice-btn-icon").textContent = "▶️";
  };

  currentSpeechUtterance.onerror = () => {
    isSpeaking = false;
    document.getElementById("voice-btn-text").textContent = "Listen Aloud";
    document.getElementById("voice-btn-icon").textContent = "▶️";
  };

  window.speechSynthesis.speak(currentSpeechUtterance);
  isSpeaking = true;
  document.getElementById("voice-btn-text").textContent = "Pause";
  document.getElementById("voice-btn-icon").textContent = "⏸️";
  showToast("Playing voice explanation...", "info");
}

function stopVoiceNarration() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    isSpeaking = false;
    document.getElementById("voice-btn-text").textContent = "Listen Aloud";
    document.getElementById("voice-btn-icon").textContent = "▶️";
  }
}

// -------------------------------------------------------------
// Feature 9: Medicines Explainer
// -------------------------------------------------------------
async function loadMedicines() {
  try {
    const res = await fetch("/api/medicines");
    const data = await res.json();
    if (data.status === "success") {
      const container = document.getElementById("medicines-grid");
      container.innerHTML = data.medicines.map(m => `
        <div style="background: #ffffff; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow-sm);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <div style="font-weight: 700; font-size: 16px; color: var(--primary);">${escapeHtml(m.medicine_name)}</div>
              <div style="font-size: 12px; color: var(--text-muted);">${escapeHtml(m.dosage)} • ${escapeHtml(m.frequency)}</div>
            </div>
            <span class="status-badge badge-normal">Active</span>
          </div>

          <div style="margin: 12px 0; font-size: 13px; line-height: 1.4;">
            <strong style="color: var(--text-main);">Clinical Purpose:</strong><br>
            ${escapeHtml(m.purpose || 'Prescribed therapy.')}
          </div>

          <div style="background: #f8fafc; padding: 10px 12px; border-radius: var(--radius-md); font-size: 12px; margin-bottom: 10px;">
            <strong>⏰ Meal Timing:</strong> ${escapeHtml(m.timing_instructions || 'As advised.')}
          </div>

          <div style="font-size: 12px; color: #b45309; background: #fffbeb; padding: 8px 12px; border-radius: var(--radius-md);">
            ⚠️ <strong>Precaution:</strong> ${escapeHtml(m.precautions || 'Consult doctor before altering dose.')}
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading medicines:", err);
  }
}

// -------------------------------------------------------------
// Feature 5: Family Access & Consent Management
// -------------------------------------------------------------
async function loadFamilyMembers() {
  try {
    const res = await fetch("/api/family");
    const data = await res.json();
    if (data.status === "success") {
      const tbody = document.getElementById("family-table-tbody");
      tbody.innerHTML = data.family_members.map(m => `
        <tr>
          <td style="font-weight: 600;">${escapeHtml(m.member_name)}</td>
          <td>${escapeHtml(m.relation)}</td>
          <td style="color: var(--text-muted); font-size: 13px;">${escapeHtml(m.member_email)}</td>
          <td><span style="font-size: 12px; font-weight: 500; background: #f1f5f9; padding: 3px 8px; border-radius: 6px;">${escapeHtml(m.permission)}</span></td>
          <td><span class="status-badge ${m.status === 'active' ? 'badge-normal' : 'badge-danger'}">${m.status.toUpperCase()}</span></td>
          <td>
            <button class="btn btn-white btn-sm" onclick="toggleFamilyAccess('${m.access_id}')">
              ${m.status === 'active' ? 'Revoke Access' : 'Restore Access'}
            </button>
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading family members:", err);
  }
}

async function toggleFamilyAccess(accessId) {
  try {
    const res = await fetch(`/api/family/${accessId}/toggle`, { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`Family access updated: ${data.new_status}`, "info");
      loadFamilyMembers();
      loadAuditLogs();
    }
  } catch (err) {
    showToast("Failed to update access", "error");
  }
}

// -------------------------------------------------------------
// Modals
// -------------------------------------------------------------
function openAddReminderModal() {
  document.getElementById("modal-reminder").classList.add("open");
}

function openAddFamilyModal() {
  document.getElementById("modal-family").classList.add("open");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("open");
}

async function saveNewReminder() {
  const rType = document.getElementById("modal-r-type").value;
  const title = document.getElementById("modal-r-title").value.trim();
  const sub = document.getElementById("modal-r-sub").value.trim();
  const time = document.getElementById("modal-r-time").value.trim();

  if (!title) {
    showToast("Please provide a title", "error");
    return;
  }

  try {
    const res = await fetch("/api/reminders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reminder_type: rType,
        title: title,
        subtitle: sub,
        scheduled_time: time || "08:00 AM"
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      closeModal("modal-reminder");
      showToast("Reminder created!", "success");
      loadDashboardData();
    }
  } catch (err) {
    showToast("Error creating reminder", "error");
  }
}

async function saveFamilyMember() {
  const name = document.getElementById("modal-f-name").value.trim();
  const email = document.getElementById("modal-f-email").value.trim();
  const relation = document.getElementById("modal-f-relation").value.trim();
  const perm = document.getElementById("modal-f-perm").value;

  if (!name || !email) {
    showToast("Please provide name and email", "error");
    return;
  }

  try {
    const res = await fetch("/api/family/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        email: email,
        relation: relation,
        permission: perm
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      closeModal("modal-family");
      showToast(`Invited ${name} successfully!`, "success");
      loadFamilyMembers();
      loadAuditLogs();
    }
  } catch (err) {
    showToast("Error granting access", "error");
  }
}

// -------------------------------------------------------------
// Audit Logs
// -------------------------------------------------------------
async function loadAuditLogs() {
  try {
    const res = await fetch("/api/audit-logs");
    const data = await res.json();
    if (data.status === "success") {
      const container = document.getElementById("audit-logs-list");
      container.innerHTML = data.logs.map(log => `
        <div style="font-size: 13px; padding: 10px 12px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between;">
          <div>
            <strong style="color: var(--primary);">${escapeHtml(log.action)}:</strong> ${escapeHtml(log.details || '')}
          </div>
          <span style="color: var(--text-muted); font-size: 11px;">${escapeHtml(log.timestamp)}</span>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading audit logs:", err);
  }
}

// Utilities
function copyText(text) {
  navigator.clipboard.writeText(text);
  showToast("Question copied to clipboard!", "success");
}

function copyAllQuestions() {
  const list = document.getElementById("doctor-questions-list");
  if (list) {
    navigator.clipboard.writeText(list.innerText);
    showToast("All questions copied to clipboard!", "success");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeQuotes(str) {
  if (!str) return "";
  return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// -------------------------------------------------------------
// Health Profile & Authentication Logic
// -------------------------------------------------------------
function openProfileTab() {
  switchTab("tab-profile");
  loadProfileData();
}

async function loadProfileData() {
  try {
    const res = await fetch("/api/profile");
    const data = await res.json();
    if (data.status === "success") {
      const p = data.profile;
      if (document.getElementById("prof-name")) document.getElementById("prof-name").value = p.name || "";
      if (document.getElementById("prof-email")) document.getElementById("prof-email").value = p.email || "";
      if (document.getElementById("prof-phone")) document.getElementById("prof-phone").value = p.phone || "";
      if (document.getElementById("prof-age")) document.getElementById("prof-age").value = p.age || 34;
      if (document.getElementById("prof-gender")) document.getElementById("prof-gender").value = p.gender || "Female";
      if (document.getElementById("prof-blood-group")) document.getElementById("prof-blood-group").value = p.blood_group || "";
      if (document.getElementById("prof-allergies")) document.getElementById("prof-allergies").value = p.allergies || "";
      if (document.getElementById("prof-chronic")) document.getElementById("prof-chronic").value = p.chronic_conditions || "";
      if (document.getElementById("prof-emergency")) document.getElementById("prof-emergency").value = p.emergency_contact || "";
      if (document.getElementById("prof-lang")) document.getElementById("prof-lang").value = p.preferred_language || "en";
      if (document.getElementById("prof-reading-level")) document.getElementById("prof-reading-level").value = p.reading_level || "standard";

      // Update header profile display
      if (document.getElementById("user-display-name")) document.getElementById("user-display-name").textContent = p.name;
      const initials = p.name.split(" ").map(n => n[0]).join("");
      if (document.getElementById("avatar-initials")) document.getElementById("avatar-initials").textContent = initials;
      if (document.getElementById("hero-greeting-text")) document.getElementById("hero-greeting-text").textContent = `Good evening, ${p.name.split(" ")[0]}! 👋`;
    }
  } catch (err) {
    console.error("Error loading profile data:", err);
  }
}

async function saveProfileChanges() {
  const payload = {
    name: document.getElementById("prof-name").value.trim(),
    email: document.getElementById("prof-email").value.trim(),
    phone: document.getElementById("prof-phone").value.trim(),
    age: parseInt(document.getElementById("prof-age").value) || 34,
    gender: document.getElementById("prof-gender").value,
    blood_group: document.getElementById("prof-blood-group").value.trim(),
    allergies: document.getElementById("prof-allergies").value.trim(),
    chronic_conditions: document.getElementById("prof-chronic").value.trim(),
    emergency_contact: document.getElementById("prof-emergency").value.trim(),
    preferred_language: document.getElementById("prof-lang").value,
    reading_level: document.getElementById("prof-reading-level").value
  };

  try {
    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Health Profile saved successfully!", "success");
      loadProfileData();
      loadDashboardData();
      loadAuditLogs();
    }
  } catch (err) {
    showToast("Failed to save profile changes", "error");
  }
}

async function handleLogout() {
  try {
    const res = await fetch("/api/auth/logout", { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast("You have been logged out securely.", "info");
      document.getElementById("modal-auth").classList.add("open");
      loadAuditLogs();
    }
  } catch (err) {
    showToast("Session ended", "info");
    document.getElementById("modal-auth").classList.add("open");
  }
}

async function handleLoginSubmit() {
  const userName = document.getElementById("login-input-name").value.trim() || "Kashish Sharma";
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: userName })
    });
    const data = await res.json();
    if (data.status === "success") {
      closeModal("modal-auth");
      showToast(data.message, "success");
      loadDashboardData();
      loadProfileData();
      loadAuditLogs();
      switchTab("tab-dashboard");
    }
  } catch (err) {
    closeModal("modal-auth");
    showToast("Logged in successfully", "success");
  }
}

// -------------------------------------------------------------
// Interactive Guided Showcase Tour
// -------------------------------------------------------------
async function startShowcaseTour() {
  showToast("✨ Starting MedBuddy Live Feature Showcase Tour!", "info");

  const steps = [
    {
      action: async () => {
        switchTab("tab-dashboard");
        showToast("Step 1: Patient Dashboard with daily doses, active medications, and health metrics.", "info");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-upload");
        showToast("Step 2: Medical File Validation (Strict rejection of non-medical files like invoices).", "info");
        await loadSampleReport("standard_lab");
      },
      delay: 4000
    },
    {
      action: async () => {
        switchTab("tab-analysis");
        showToast("Step 3: Plain-Language Summary & Medical Jargon Explanations generated.", "info");
      },
      delay: 4000
    },
    {
      action: async () => {
        showToast("Step 4: Adapting Reading Level to Simple (Everyday Words)...", "info");
        await setReadingLevel("simple");
      },
      delay: 3500
    },
    {
      action: async () => {
        showToast("Step 5: Multilingual Translation to हिन्दी (Hindi) with exact numbers preserved...", "info");
        document.getElementById("language-switcher").value = "hi";
        await applyLanguage("hi");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-lab-values");
        showToast("Step 6: Deterministic Laboratory Value Status with visual range progress gauges.", "info");
      },
      delay: 4000
    },
    {
      action: async () => {
        showToast("Step 7: Evaluating emergency report for Critical Red-Flag Alerts...", "info");
        await loadSampleReport("critical_alert");
        switchTab("tab-red-flags");
      },
      delay: 4500
    },
    {
      action: async () => {
        switchTab("tab-medicines");
        showToast("Step 8: Prescribed Medicine Explainer with clinical purpose and meal timings.", "info");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-doctor-q");
        showToast("Step 9: Contextual Questions derived for Doctor Consultation preparation.", "info");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-family");
        showToast("Step 10: Patient-Controlled Caregiver Access & Immutable Audit Logging.", "info");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-profile");
        showToast("Step 11: Patient Health Profile with allergy alerts and emergency contact.", "info");
      },
      delay: 3500
    },
    {
      action: async () => {
        switchTab("tab-dashboard");
        document.getElementById("language-switcher").value = "en";
        await applyLanguage("en");
        showToast("🎉 Showcase Tour Complete! All 12 PRD features successfully demonstrated.", "success");
      },
      delay: 2000
    }
  ];

  for (const step of steps) {
    await step.action();
    await new Promise(resolve => setTimeout(resolve, step.delay));
  }
}
