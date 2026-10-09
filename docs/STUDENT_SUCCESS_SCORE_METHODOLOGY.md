# Student Success Score & AI Risk Prediction Methodology

This document provides the mathematical, analytical, and operational specification for the **Explainable Student Success Score** and **AI Risk Classification Engine** used in the **Smart Campus Analytics Platform**.

---

## 🎯 1. Purpose & Core Objective

The Student Success Score is an institutional early-warning indicator ($0 - 100$) designed to help college faculty, counselors, and placement officers identify students requiring targeted support before academic failure or placement disengagement occurs.

Rather than relying on isolated metrics (such as CGPA alone), the platform synthesizes academic performance, attendance compliance, learning management system (LMS) activity, career readiness, and skill assessments into a single explainable score.

---

## 📊 2. Indicator Domains & Configured Weights

The composite Student Success Score is computed using a weighted linear combination across 5 core domains:

$$\text{Success Score} = 0.30 S_{\text{academic}} + 0.25 S_{\text{attendance}} + 0.15 S_{\text{lms}} + 0.15 S_{\text{placement}} + 0.15 S_{\text{skills\_engagement}}$$

### Domain Breakdown & Calculations:

| Domain | Weight | Calculation & Inputs |
| :--- | :--- | :--- |
| **Academic Performance ($S_{\text{academic}}$)** | **30%** | $\text{CGPA} \times 10 - (\text{Backlog Count} \times 10)$, clamped to $[0, 100]$. Penalizes active backlog failures. |
| **Attendance Compliance ($S_{\text{attendance}}$)** | **25%** | Overall Attendance Percentage ($\frac{\text{Classes Attended}}{\text{Total Conducted}} \times 100$). Severe penalty cap ($40/100$) applied if attendance $< 60\%$. |
| **LMS Engagement ($S_{\text{lms}}$)** | **15%** | $0.40(\text{Assignment Comp \%}) + 0.30(\text{Timeliness \%}) + 0.20(\text{Quiz \%}) + 0.10(\text{Logins Normalized})$. Inactivity penalty subtracted if inactive $> 7$ days. |
| **Placement Readiness ($S_{\text{placement}}$)** | **15%** | Mean of Aptitude, Coding, Mock Interview, Resume Readiness, and Communication assessment scores. |
| **Skills & Engagement ($S_{\text{skills\_engagement}}$)** | **15%** | $0.60(\text{Avg Technical/Soft Skill Score}) + 0.40(\text{Extracurricular Hackathon/Club Score})$. |

---

## ⚠️ 3. Missing Data & Data Completeness

When a student lacks records in a specific category (e.g. a 1st-year student with no placement assessment):
- The engine assigns a benchmark population baseline ($50.0 - 70.0$) rather than defaulting to $0.0$.
- The `explanation_json` metadata flags missing indicators explicitly under `data_availability` to prevent misleading risk attribution.

---

## 🚦 4. Risk Classification Rules

Students are assigned an **Academic & Attendance Risk Level** based on deterministic decision boundary rules:

- 🔴 **CRITICAL RISK**: $\text{CGPA} < 5.0$ **OR** $\text{Attendance} < 60\%$ **OR** $\text{Backlogs} \ge 3$ **OR** $\text{Success Score} < 45.0$.
- 🟠 **HIGH RISK**: $\text{CGPA} < 6.5$ **OR** $\text{Attendance} < 75\%$ **OR** $\text{Backlogs} \ge 1$ **OR** $\text{Success Score} < 60.0$.
- 🟡 **MEDIUM RISK**: $\text{CGPA} < 7.5$ **OR** $\text{Attendance} < 85\%$ **OR** $\text{Success Score} < 75.0$.
- 🟢 **LOW RISK**: $\text{CGPA} \ge 7.5$, $\text{Attendance} \ge 85\%$, 0 backlogs, and $\text{Success Score} \ge 75.0$.

---

## 🔍 5. Explainability Schema & Automated Interventions

Each calculation outputs a structured JSON breakdown stored in `StudentSuccessSnapshot.explanation_json`:

```json
{
  "cgpa": 5.5,
  "backlog_count": 2,
  "attendance_percentage": 68.5,
  "sub_scores": {
    "academic_score": 35.0,
    "attendance_score": 68.5,
    "lms_score": 55.0,
    "placement_score": 48.0,
    "skills_engagement_score": 60.0
  },
  "positive_factors": [],
  "risk_flags": [
    "Low CGPA Warning: 5.50",
    "Active Backlogs: 2",
    "Mandatory Attendance Deficit: 68.5% (Below 75% threshold)"
  ],
  "recommended_interventions": [
    "ACADEMIC_TUTORING",
    "ATTENDANCE_COUNSELING"
  ]
}
```

---

## 📌 6. Technical Limitations & Future Enhancements

1. **Rule-Based Weights**: Initial weights reflect institutional guidelines. Future phases can train logistic regression or gradient boosting models on multi-year longitudinal outcome datasets.
2. **Advisory Tool**: The score is designed as a decision-support aid for advisors and should never automatically penalize students without human faculty review.
