"""CSV & Excel Student Risk Checker Service.

Parses tabular student records and applies the explainable Student Analytics Engine
to determine risk level, risk flags, composite scores, and intervention recommendations
without requiring prior database persistence, while supporting optional bulk import.
"""
import io
import math
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
from pathlib import Path
import pandas as pd

from apps.analytics.models import StudentSuccessSnapshot
from apps.interventions.models import InterventionRecord


class CSVRiskCheckerService:
    """Service for analyzing student risk directly from uploaded CSV or Excel files."""

    COLUMN_SPECS = [
        {
            "name": "student_id",
            "required": True,
            "type": "Text (Alphanumeric)",
            "range": "e.g., STU2025101",
            "risk_impact": "Unique primary identifier for student records and matching.",
            "example": "STU2025101",
        },
        {
            "name": "name",
            "required": False,
            "type": "Text",
            "range": "Full student name",
            "risk_impact": "Display name in risk directory and personalized alert notifications.",
            "example": "Jane Doe",
        },
        {
            "name": "department",
            "required": False,
            "type": "Text Code",
            "range": "CSE, ECE, EEE, MECH, etc.",
            "risk_impact": "Department-level cohort grouping and faculty-scoped risk management.",
            "example": "CSE",
        },
        {
            "name": "semester",
            "required": False,
            "type": "Integer",
            "range": "1 to 8",
            "risk_impact": "Curriculum milestone indicator for graduation & placement readiness.",
            "example": "5",
        },
        {
            "name": "cgpa",
            "required": False,
            "type": "Decimal",
            "range": "0.00 - 10.00",
            "risk_impact": "30% score weight. CGPA < 6.5 triggers High Risk; CGPA < 5.0 triggers Critical Risk.",
            "example": "7.85",
        },
        {
            "name": "attendance_percentage",
            "required": False,
            "type": "Percentage",
            "range": "0.0 - 100.0%",
            "risk_impact": "25% score weight. < 75% triggers Attendance Warning; < 60% triggers Critical Risk.",
            "example": "88.5",
        },
        {
            "name": "backlog_count",
            "required": False,
            "type": "Integer",
            "range": "0, 1, 2, ...",
            "risk_impact": "Severe academic penalty (-10 pts per backlog). >= 1 triggers High Risk.",
            "example": "0",
        },
        {
            "name": "lms_login_frequency",
            "required": False,
            "type": "Integer",
            "range": "Logins/month (0 - 50+)",
            "risk_impact": "LMS activity frequency. Inactive students flagged as LMS Disengaged.",
            "example": "22",
        },
        {
            "name": "assignment_completion_percentage",
            "required": False,
            "type": "Percentage",
            "range": "0.0 - 100.0%",
            "risk_impact": "LMS sub-score weight (15%). Completion < 65% triggers LMS Risk Flag.",
            "example": "92.0",
        },
        {
            "name": "coding_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Placement readiness sub-score (15%). Score < 55 triggers Weak Coding Flag.",
            "example": "85.0",
        },
        {
            "name": "aptitude_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Aptitude assessment. Score < 60 triggers Placement Prep recommendation.",
            "example": "78.0",
        },
        {
            "name": "mock_interview_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Soft-skill interview readiness indicator.",
            "example": "80.0",
        },
        {
            "name": "technical_skill_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Technical proficiencies (15% combined skills & engagement sub-score).",
            "example": "84.0",
        },
        {
            "name": "soft_skill_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Communication, team collaboration, and leadership score.",
            "example": "76.0",
        },
        {
            "name": "engagement_score",
            "required": False,
            "type": "Decimal",
            "range": "0.0 - 100.0",
            "risk_impact": "Campus extracurricular and co-curricular participation.",
            "example": "72.0",
        },
        {
            "name": "feedback_score",
            "required": False,
            "type": "Integer Rating",
            "range": "1 to 5",
            "risk_impact": "Confidential student feedback and satisfaction index.",
            "example": "4",
        },
    ]

    CANONICAL_HEADERS = [
        "student_id",
        "name",
        "department",
        "semester",
        "cgpa",
        "attendance_percentage",
        "backlog_count",
        "lms_login_frequency",
        "assignment_completion_percentage",
        "coding_score",
        "aptitude_score",
        "mock_interview_score",
        "technical_skill_score",
        "soft_skill_score",
        "engagement_score",
        "feedback_score",
    ]

    SYNONYM_MAP = {
        "studentid": "student_id",
        "student id": "student_id",
        "roll_no": "student_id",
        "rollno": "student_id",
        "usn": "student_id",
        "id": "student_id",
        "student_name": "name",
        "studentname": "name",
        "student name": "name",
        "full_name": "name",
        "fullname": "name",
        "dept": "department",
        "branch": "department",
        "department_name": "department",
        "dept_name": "department",
        "sem": "semester",
        "gpa": "cgpa",
        "sgpa": "cgpa",
        "attendance": "attendance_percentage",
        "attendance_pct": "attendance_percentage",
        "attendance%": "attendance_percentage",
        "attendance_percentage": "attendance_percentage",
        "backlogs": "backlog_count",
        "backlog": "backlog_count",
        "backlog_count": "backlog_count",
        "arrears": "backlog_count",
        "lms_logins": "lms_login_frequency",
        "login_frequency": "lms_login_frequency",
        "lms_login_frequency": "lms_login_frequency",
        "lms_completion": "assignment_completion_percentage",
        "lms_completion_percentage": "assignment_completion_percentage",
        "lms_completion_pct": "assignment_completion_percentage",
        "assignment_completion": "assignment_completion_percentage",
        "assignment_completion_pct": "assignment_completion_percentage",
        "assignment_completion_percentage": "assignment_completion_percentage",
        "assignments": "assignment_completion_percentage",
        "coding": "coding_score",
        "coding_score": "coding_score",
        "aptitude": "aptitude_score",
        "aptitude_score": "aptitude_score",
        "interview": "mock_interview_score",
        "mock_interview": "mock_interview_score",
        "mock_interview_score": "mock_interview_score",
        "resume": "resume_readiness_score",
        "resume_score": "resume_readiness_score",
        "resume_readiness_score": "resume_readiness_score",
        "communication": "communication_score",
        "communication_score": "communication_score",
        "tech_skills": "technical_skill_score",
        "technical_skill": "technical_skill_score",
        "technical_skills": "technical_skill_score",
        "technical_skill_score": "technical_skill_score",
        "soft_skills": "soft_skill_score",
        "soft_skill": "soft_skill_score",
        "soft_skill_score": "soft_skill_score",
        "engagement": "engagement_score",
        "engagement_score": "engagement_score",
        "feedback": "feedback_score",
        "feedback_score": "feedback_score",
    }

    @classmethod
    def get_canonical_header_csv(cls) -> str:
        return ",".join(cls.CANONICAL_HEADERS)

    @classmethod
    def _to_float(cls, val, default=None):
        if val is None or pd.isna(val):
            return default
        try:
            num = float(val)
            return num if math.isfinite(num) else default
        except (ValueError, TypeError):
            return default

    @classmethod
    def _to_int(cls, val, default=None):
        num = cls._to_float(val, default)
        return int(num) if num is not None else default

    @classmethod
    def analyze_file(cls, file_obj, filename="dataset.csv") -> dict:
        """Parses an uploaded file buffer or path and evaluates risk for all student rows."""
        ext = Path(filename).suffix.lower()

        if hasattr(file_obj, "read"):
            content = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            buffer = io.BytesIO(content)
        else:
            buffer = file_obj

        if ext == ".csv":
            try:
                df = pd.read_csv(buffer)
            except UnicodeDecodeError:
                if hasattr(buffer, "seek"):
                    buffer.seek(0)
                df = pd.read_csv(buffer, encoding="latin-1")
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(buffer)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Please upload a .csv, .xlsx, or .xls file.")

        return cls.analyze_dataframe(df, filename=filename)

    @classmethod
    def analyze_dataframe(cls, df: pd.DataFrame, filename="dataset.csv") -> dict:
        if df.empty:
            return {
                "filename": filename,
                "total_rows": 0,
                "valid_rows": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "at_risk_count": 0,
                "safe_count": 0,
                "avg_success_score": 0.0,
                "avg_cgpa": 0.0,
                "avg_attendance": 0.0,
                "records": [],
                "errors": ["The uploaded file contains no data rows."],
                "columns_found": [],
            }

        # Normalize column headers
        raw_cols = [str(c).strip().lower() for c in df.columns]
        renamed_cols = [cls.SYNONYM_MAP.get(c, c) for c in raw_cols]
        df.columns = renamed_cols

        errors = []
        if "student_id" not in df.columns:
            raise ValueError("Required column missing: 'student_id'. Please check your CSV column headers.")

        records = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for idx, row in df.iterrows():
            row_num = idx + 2
            sid_val = row.get("student_id", "")
            if pd.isna(sid_val) or str(sid_val).strip() == "":
                errors.append(f"Row {row_num}: Missing student_id.")
                continue

            student_id = str(sid_val).strip().upper()
            name = str(row.get("name", "")).strip() if "name" in df.columns and not pd.isna(row.get("name")) else student_id
            dept = str(row.get("department", "GEN")).strip().upper() if "department" in df.columns and not pd.isna(row.get("department")) else "GEN"
            semester = cls._to_int(row.get("semester"), default=5)

            # Core Metrics
            raw_cgpa = cls._to_float(row.get("cgpa"))
            cgpa = raw_cgpa if raw_cgpa is not None else 7.0

            raw_attendance = cls._to_float(row.get("attendance_percentage"))
            attendance_pct = raw_attendance if raw_attendance is not None else 80.0

            raw_backlogs = cls._to_int(row.get("backlog_count"))
            backlogs = raw_backlogs if raw_backlogs is not None else 0

            # LMS Metrics
            comp_pct = cls._to_float(row.get("assignment_completion_percentage"), default=70.0)
            login_freq = cls._to_float(row.get("lms_login_frequency"), default=20.0)

            # Placement Metrics
            coding_score = cls._to_float(row.get("coding_score"), default=65.0)
            aptitude_score = cls._to_float(row.get("aptitude_score"), default=65.0)
            mock_score = cls._to_float(row.get("mock_interview_score"), default=65.0)

            # Skills & Engagement
            tech_skill = cls._to_float(row.get("technical_skill_score"), default=70.0)
            soft_skill = cls._to_float(row.get("soft_skill_score"), default=70.0)
            engagement = cls._to_float(row.get("engagement_score"), default=50.0)

            # 1. Academic Sub-Score (Weight: 30%)
            academic_score = max(0.0, min(100.0, (cgpa * 10.0) - (backlogs * 10.0)))

            # 2. Attendance Sub-Score (Weight: 25%)
            attendance_score = attendance_pct
            if attendance_pct < 60.0:
                attendance_score = min(attendance_score, 40.0)

            # 3. LMS Engagement Sub-Score (Weight: 15%)
            login_freq_score = min(100.0, (login_freq / 20.0) * 100.0)
            lms_score = (0.40 * comp_pct) + (0.30 * 80.0) + (0.20 * 75.0) + (0.10 * login_freq_score)

            # 4. Placement Readiness Sub-Score (Weight: 15%)
            placement_score = (0.40 * coding_score) + (0.30 * aptitude_score) + (0.30 * mock_score)

            # 5. Skills & Engagement Sub-Score (Weight: 15%)
            avg_skills = (tech_skill + soft_skill) / 2.0
            skills_eng_score = (0.60 * avg_skills) + (0.40 * engagement)

            # Composite Success Score (0 - 100)
            overall_success_score = round(
                (0.30 * academic_score)
                + (0.25 * attendance_score)
                + (0.15 * lms_score)
                + (0.15 * placement_score)
                + (0.15 * skills_eng_score),
                1,
            )

            # Risk Factors & Flags
            risk_flags = []
            positive_factors = []
            recommended_interventions = []

            if cgpa >= 8.5:
                positive_factors.append(f"Outstanding CGPA: {cgpa:.2f}")
            elif cgpa < 6.0:
                risk_flags.append(f"Low CGPA Warning: {cgpa:.2f}")

            if backlogs > 0:
                risk_flags.append(f"Active Backlogs: {backlogs}")

            if attendance_pct >= 90.0:
                positive_factors.append(f"Excellent Attendance: {attendance_pct:.1f}%")
            elif attendance_pct < 75.0:
                risk_flags.append(f"Mandatory Attendance Deficit: {attendance_pct:.1f}% (Below 75% threshold)")

            if comp_pct < 65.0:
                risk_flags.append(f"Low LMS Assignment Completion: {comp_pct:.1f}%")

            if coding_score < 55.0:
                risk_flags.append(f"Weak Coding Proficiency: {coding_score:.1f}%")

            # Risk Level Determination
            if cgpa < 5.0 or attendance_pct < 60.0 or backlogs >= 3 or overall_success_score < 45.0:
                risk_level = "CRITICAL"
                critical_count += 1
            elif cgpa < 6.5 or attendance_pct < 75.0 or backlogs >= 1 or overall_success_score < 60.0:
                risk_level = "HIGH"
                high_count += 1
            elif cgpa < 7.5 or attendance_pct < 85.0 or overall_success_score < 75.0:
                risk_level = "MEDIUM"
                medium_count += 1
            else:
                risk_level = "LOW"
                low_count += 1

            # Recommended Interventions
            if cgpa < 6.5 or backlogs > 0:
                recommended_interventions.append("Academic Tutoring")
            if attendance_pct < 75.0:
                recommended_interventions.append("Attendance Counseling")
            if coding_score < 60.0 or aptitude_score < 60.0:
                recommended_interventions.append("Placement Prep")
            if lms_score < 60.0:
                recommended_interventions.append("LMS Engagement Support")

            # Student Segment
            if overall_success_score >= 85.0 and cgpa >= 8.5 and attendance_pct >= 85.0:
                segment = "High Performing"
            elif cgpa < 6.5 or backlogs > 0:
                segment = "Academic Risk"
            elif attendance_pct < 75.0:
                segment = "Attendance Risk"
            elif cgpa >= 7.0 and coding_score < 60.0:
                segment = "Placement Support Needed"
            elif comp_pct < 60.0:
                segment = "LMS Disengaged"
            else:
                segment = "On Track / General Student"

            is_at_risk = risk_level in ["CRITICAL", "HIGH", "MEDIUM"]

            records.append({
                "row_num": row_num,
                "student_id": student_id,
                "name": name,
                "department": dept,
                "semester": semester,
                "cgpa": round(cgpa, 2),
                "attendance_percentage": round(attendance_pct, 1),
                "backlog_count": backlogs,
                "overall_success_score": overall_success_score,
                "sub_scores": {
                    "academic": round(academic_score, 1),
                    "attendance": round(attendance_score, 1),
                    "lms": round(lms_score, 1),
                    "placement": round(placement_score, 1),
                    "skills": round(skills_eng_score, 1),
                },
                "risk_level": risk_level,
                "is_at_risk": is_at_risk,
                "risk_flags": risk_flags,
                "positive_factors": positive_factors,
                "recommended_interventions": recommended_interventions,
                "segment": segment,
            })

        total_valid = len(records)
        avg_score = round(sum(r["overall_success_score"] for r in records) / total_valid, 1) if total_valid else 0.0
        avg_cgpa = round(sum(r["cgpa"] for r in records) / total_valid, 2) if total_valid else 0.0
        avg_att = round(sum(r["attendance_percentage"] for r in records) / total_valid, 1) if total_valid else 0.0

        return {
            "filename": filename,
            "total_rows": total_valid + len(errors),
            "valid_rows": total_valid,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "at_risk_count": critical_count + high_count + medium_count,
            "safe_count": low_count,
            "avg_success_score": avg_score,
            "avg_cgpa": avg_cgpa,
            "avg_attendance": avg_att,
            "records": records,
            "errors": errors,
            "columns_found": list(df.columns),
        }
