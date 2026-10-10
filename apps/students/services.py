import os
import random
import re
import numpy as np
import pandas as pd
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile, FacultyAssignment
from apps.academics.models import Subject, SemesterResult, AssessmentResult
from apps.attendance.models import AttendanceRecord
from apps.lms.models import LMSActivitySummary
from apps.engagement.models import ActivityCategory, EngagementActivity, StudentEngagement
from apps.placements.models import PlacementAssessment, PlacementApplication
from apps.skills.models import Skill, StudentSkillAssessment
from apps.feedback.models import FeedbackCategory, StudentFeedback, FacultyFeedback
from apps.analytics.models import StudentSuccessSnapshot
from apps.interventions.models import InterventionRecord

User = get_user_model()

class DataImportService:
    """Validate and import a combined student dataset from CSV or Excel."""

    SYNONYM_MAP = {
        "studentid": "student_id",
        "student_id": "student_id",
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
    def _resolve_department(cls, raw_value) -> tuple[str, str]:
        """
        Resolves a raw department string (code, abbreviation, or full name)
        into a valid (dept_code, dept_name) tuple.
        Guarantees dept_code matches [A-Z0-9_-]{1,20}.
        """
        val = str(raw_value).strip() if raw_value is not None and not pd.isna(raw_value) else ""
        if not val or val.upper() in {"GENERAL", "NONE", "NAN", "NULL", ""}:
            return "GENERAL", "Department of GENERAL"

        val_upper = val.upper()
        # Cleaned alphanumeric string without spaces or punctuation
        val_clean = re.sub(r"[^A-Z0-9]", "", val_upper)

        KNOWN_ALIASES = {
            "CSE": ("CSE", "Computer Science & Engineering"),
            "CS": ("CSE", "Computer Science & Engineering"),
            "COMPUTERSCIENCE": ("CSE", "Computer Science & Engineering"),
            "COMPUTERSCIENCEENGINEERING": ("CSE", "Computer Science & Engineering"),
            "COMPUTERSCIENCEANDENGINEERING": ("CSE", "Computer Science & Engineering"),
            "ECE": ("ECE", "Electronics & Communication"),
            "EC": ("ECE", "Electronics & Communication"),
            "ELECTRONICSCOMMUNICATION": ("ECE", "Electronics & Communication"),
            "ELECTRONICSANDCOMMUNICATION": ("ECE", "Electronics & Communication"),
            "ELECTRONICSCOMMUNICATIONENGINEERING": ("ECE", "Electronics & Communication"),
            "ELECTRONICSANDCOMMUNICATIONENGINEERING": ("ECE", "Electronics & Communication"),
            "EEE": ("EEE", "Electrical & Electronics"),
            "EE": ("EEE", "Electrical & Electronics"),
            "ELECTRICALELECTRONICS": ("EEE", "Electrical & Electronics"),
            "ELECTRICALANDELECTRONICS": ("EEE", "Electrical & Electronics"),
            "ELECTRICALELECTRONICSENGINEERING": ("EEE", "Electrical & Electronics"),
            "ELECTRICALANDELECTRONICSENGINEERING": ("EEE", "Electrical & Electronics"),
            "MECH": ("MECH", "Mechanical Engineering"),
            "ME": ("MECH", "Mechanical Engineering"),
            "MECHANICAL": ("MECH", "Mechanical Engineering"),
            "MECHANICALENGINEERING": ("MECH", "Mechanical Engineering"),
            "IT": ("IT", "Information Technology"),
            "INFORMATIONTECHNOLOGY": ("IT", "Information Technology"),
            "CIVIL": ("CIVIL", "Civil Engineering"),
            "CE": ("CIVIL", "Civil Engineering"),
            "CIVILENGINEERING": ("CIVIL", "Civil Engineering"),
            "AIDS": ("AI_DS", "Artificial Intelligence & Data Science"),
            "ARTIFICIALINTELLIGENCEDATASCIENCE": ("AI_DS", "Artificial Intelligence & Data Science"),
            "ARTIFICIALINTELLIGENCEANDDATASCIENCE": ("AI_DS", "Artificial Intelligence & Data Science"),
            "AIML": ("AI_ML", "Artificial Intelligence & Machine Learning"),
            "ARTIFICIALINTELLIGENCEMACHINELEARNING": ("AI_ML", "Artificial Intelligence & Machine Learning"),
            "DS": ("DS", "Data Science"),
            "DATASCIENCE": ("DS", "Data Science"),
            "CYBER": ("CYBER", "Cyber Security"),
            "CYBERSECURITY": ("CYBER", "Cyber Security"),
            "BIOTECH": ("BIOTECH", "Biotechnology"),
            "BIOTECHNOLOGY": ("BIOTECH", "Biotechnology"),
            "CHEMICAL": ("CHEM", "Chemical Engineering"),
            "CHEMICALENGINEERING": ("CHEM", "Chemical Engineering"),
            "AERO": ("AERO", "Aeronautical Engineering"),
            "AEROSPACE": ("AERO", "Aerospace Engineering"),
            "AUTOMOBILE": ("AUTO", "Automobile Engineering"),
        }

        if val_clean in KNOWN_ALIASES:
            return KNOWN_ALIASES[val_clean]

        # Check existing departments in the database by code or name
        dept = (
            Department.objects.filter(code__iexact=val).first()
            or Department.objects.filter(name__iexact=val).first()
            or Department.objects.filter(name__icontains=val).first()
        )
        if dept:
            return dept.code, dept.name

        # Valid short code (1 to 20 alphanumeric, hyphen, underscore)
        if re.fullmatch(r"[A-Z0-9_-]{1,20}", val_upper):
            return val_upper, f"Department of {val_upper}"

        # Multi-word string: generate code from initials (e.g. "Robotics & Automation" -> "RA")
        words = [w for w in re.split(r"[\s&_\-]+", val_upper) if w and w not in {"AND", "OF", "&", "THE", "DEPARTMENT"}]
        initials = "".join(w[0] for w in words if w[0].isalnum())
        if 2 <= len(initials) <= 10:
            return initials, val[:150]

        # Sanitize directly
        sanitized = re.sub(r"[^A-Z0-9_-]", "", val_upper.replace(" ", "_"))[:20]
        if sanitized:
            return sanitized, val[:150]

        return "GENERAL", "General Department"

    @staticmethod
    def _value(row, key, default=""):
        value = row.get(key, default)
        if pd.isna(value):
            return default
        return value

    @classmethod
    def _number(cls, row, key, default, minimum, maximum, row_num, errors, integer=False):
        raw = row.get(key, default)
        if key in row.index and (pd.isna(raw) or str(raw).strip() == ""):
            errors.append(f"Row {row_num}: {key} is missing.")
            return None
        try:
            number = float(raw)
            if not np.isfinite(number):
                raise ValueError
            if not minimum <= number <= maximum:
                errors.append(f"Row {row_num}: {key} must be between {minimum} and {maximum}.")
                return None
            if integer and not number.is_integer():
                errors.append(f"Row {row_num}: {key} must be a whole number.")
                return None
            return int(number) if integer else number
        except (TypeError, ValueError):
            errors.append(f"Row {row_num}: {key} must be a valid number.")
            return None

    @classmethod
    def import_from_file(cls, file_path, evaluate_analytics=False):
        if not os.path.isfile(file_path):
            raise FileNotFoundError("Import file was not found.")

        suffix = os.path.splitext(file_path)[1].lower()
        if suffix == ".csv":
            df = pd.read_csv(file_path)
        elif suffix in {".xls", ".xlsx"}:
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")
        if df.empty:
            return {"imported_count": 0, "errors": ["The uploaded file contains no records."]}
        raw_cols = [str(column).strip().lower() for column in df.columns]
        df.columns = [cls.SYNONYM_MAP.get(c, cls.SYNONYM_MAP.get(c.replace(" ", "_").replace("-", "_"), c)) for c in raw_cols]
        if "student_id" not in df.columns:
            raise ValueError("Required column missing: student_id")

        imported_count = 0
        errors = []
        current_year = timezone.localdate().year
        academic_year = AcademicYear.objects.filter(is_current=True).order_by("-year_label").first()

        def ensure_academic_year():
            nonlocal academic_year
            if academic_year is None:
                academic_year, _ = AcademicYear.objects.get_or_create(
                    year_label=f"{current_year}-{current_year + 1}", defaults={"is_current": True}
                )
            return academic_year

        with transaction.atomic():
            for idx, row in df.iterrows():
                row_num = idx + 2
                student_id_value = cls._value(row, "student_id", "")
                if isinstance(student_id_value, (float, np.floating)) and float(student_id_value).is_integer():
                    student_id_value = int(student_id_value)
                student_id = str(student_id_value).strip().upper()
                if not student_id:
                    errors.append(f"Row {row_num}: Missing student_id.")
                    continue

                name_value = cls._value(row, "name", "")
                name = str(name_value).strip()
                first_name = name.split()[0] if name else "Student"
                last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else student_id
                email = str(cls._value(row, "email", f"{student_id.lower()}@campus.edu")).strip()
                dept_raw = cls._value(row, "department", "GENERAL")
                dept_code, dept_display_name = cls._resolve_department(dept_raw)
                semester_number = cls._number(row, "semester", 1, 1, 8, row_num, errors, integer=True) if "semester" in df.columns else 1
                admission_default = max(2000, current_year - semester_number // 2) if semester_number is not None else current_year
                admission_year = cls._number(row, "admission_year", admission_default, 2000, current_year, row_num, errors, integer=True) if "admission_year" in df.columns else admission_default
                cgpa = cls._number(row, "cgpa", 7.0, 0, 10, row_num, errors) if "cgpa" in df.columns else None
                backlog_count = cls._number(row, "backlog_count", 0, 0, 100, row_num, errors, integer=True) if "backlog_count" in df.columns else 0
                attendance_pct = cls._number(row, "attendance_percentage", 80.0, 0, 100, row_num, errors) if "attendance_percentage" in df.columns else None
                login_frequency = cls._number(row, "lms_login_frequency", 15, 0, 10000, row_num, errors, integer=True) if "lms_login_frequency" in df.columns else 15
                completion_pct = cls._number(row, "assignment_completion_percentage", 85.0, 0, 100, row_num, errors) if "assignment_completion_percentage" in df.columns else 85.0
                aptitude_score = cls._number(row, "aptitude_score", 65.0, 0, 100, row_num, errors) if "aptitude_score" in df.columns else 65.0
                coding_score = cls._number(row, "coding_score", 60.0, 0, 100, row_num, errors) if "coding_score" in df.columns else 60.0
                mock_score = cls._number(row, "mock_interview_score", 65.0, 0, 100, row_num, errors) if "mock_interview_score" in df.columns else 65.0
                resume_score = cls._number(row, "resume_readiness_score", 65.0, 0, 100, row_num, errors) if "resume_readiness_score" in df.columns else 65.0
                communication_score = cls._number(row, "communication_score", 65.0, 0, 100, row_num, errors) if "communication_score" in df.columns else 65.0
                engagement_score = cls._number(row, "engagement_score", 50.0, 0, 100, row_num, errors) if "engagement_score" in df.columns else 50.0
                technical_skill_score = cls._number(row, "technical_skill_score", 50.0, 0, 100, row_num, errors) if "technical_skill_score" in df.columns else 50.0
                soft_skill_score = cls._number(row, "soft_skill_score", 50.0, 0, 100, row_num, errors) if "soft_skill_score" in df.columns else 50.0
                feedback_score = cls._number(row, "feedback_score", 3, 1, 5, row_num, errors, integer=True) if "feedback_score" in df.columns else None
                if admission_year is None or ("cgpa" in df.columns and cgpa is None) or ("attendance_percentage" in df.columns and attendance_pct is None):
                    continue
                if any(value is None for value in (semester_number, backlog_count, login_frequency, completion_pct, aptitude_score, coding_score, mock_score, resume_score, communication_score, engagement_score, technical_skill_score, soft_skill_score)) or ("feedback_score" in df.columns and feedback_score is None):
                    continue

                if not email:
                    email = f"{student_id.lower()}@campus.edu"
                try:
                    validate_email(email)
                except ValidationError:
                    errors.append(f"Row {row_num}: Invalid email address.")
                    continue
                if StudentProfile.objects.filter(email=email).exclude(student_id=student_id).exists():
                    errors.append(f"Row {row_num}: Email address is already assigned to another student.")
                    continue

                row_dept, _ = Department.objects.get_or_create(
                    code=dept_code,
                    defaults={"name": dept_display_name},
                )
                row_program, _ = Program.objects.get_or_create(
                    code=f"{dept_code}-BTECH",
                    defaults={"name": f"B.Tech in {dept_display_name}", "department": row_dept},
                )
                student, _created = StudentProfile.objects.update_or_create(
                    student_id=student_id,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "department": row_dept,
                        "program": row_program,
                        "current_semester": semester_number,
                        "admission_year": admission_year,
                    },
                )
                if cgpa is not None:
                    semester, _ = Semester.objects.get_or_create(number=semester_number, academic_year=ensure_academic_year())
                    SemesterResult.objects.update_or_create(
                        student=student,
                        semester=semester,
                        defaults={"sgpa": cgpa, "cgpa": cgpa, "backlog_count": backlog_count},
                    )
                if attendance_pct is not None:
                    semester, _ = Semester.objects.get_or_create(number=semester_number, academic_year=ensure_academic_year())
                    AttendanceRecord.objects.update_or_create(
                        student=student,
                        semester=semester,
                        subject=None,
                        defaults={"total_classes": 100, "classes_attended": round(attendance_pct)},
                    )
                if any(column in df.columns for column in ("lms_login_frequency", "assignment_completion_percentage")):
                    LMSActivitySummary.objects.update_or_create(
                        student=student,
                        defaults={
                            "login_frequency": login_frequency,
                            "assignment_completion_pct": completion_pct,
                            "last_activity_date": timezone.now(),
                        },
                    )
                if any(column in df.columns for column in ("aptitude_score", "coding_score", "mock_interview_score", "resume_readiness_score", "communication_score")):
                    PlacementAssessment.objects.update_or_create(
                        student=student,
                        defaults={"aptitude_score": aptitude_score, "coding_score": coding_score,
                                  "mock_interview_score": mock_score,
                                  "resume_readiness_score": resume_score,
                                  "communication_score": communication_score},
                    )
                if "engagement_score" in df.columns:
                    category, _ = ActivityCategory.objects.get_or_create(name="Imported Engagement")
                    activity, _ = EngagementActivity.objects.get_or_create(
                        title="Imported Engagement Score", category=category,
                        defaults={"event_date": timezone.localdate(), "organizer": "Dataset Import"},
                    )
                    StudentEngagement.objects.update_or_create(
                        student=student, activity=activity,
                        defaults={"engagement_score": engagement_score, "role": "Imported"},
                    )
                if "technical_skill_score" in df.columns:
                    skill, _ = Skill.objects.get_or_create(name="Technical Skills", defaults={"category": Skill.SkillCategory.TECHNICAL})
                    StudentSkillAssessment.objects.update_or_create(
                        student=student, skill=skill, defaults={"proficiency_score": technical_skill_score},
                    )
                if "soft_skill_score" in df.columns:
                    skill, _ = Skill.objects.get_or_create(name="Soft Skills", defaults={"category": Skill.SkillCategory.SOFT_SKILL})
                    StudentSkillAssessment.objects.update_or_create(
                        student=student, skill=skill, defaults={"proficiency_score": soft_skill_score},
                    )
                if feedback_score is not None:
                    category, _ = FeedbackCategory.objects.get_or_create(name="Imported Student Feedback")
                    feedback = StudentFeedback.objects.filter(student=student, category=category).order_by("-submitted_date").first()
                    if feedback:
                        feedback.satisfaction_score = feedback_score
                        feedback.save(update_fields=["satisfaction_score"])
                    else:
                        StudentFeedback.objects.create(student=student, category=category, satisfaction_score=feedback_score, is_confidential=True)

                if evaluate_analytics:
                    try:
                        import logging
                        from apps.analytics.services import StudentAnalyticsEngine
                        StudentAnalyticsEngine.evaluate_and_save_snapshot(student)
                    except Exception as eval_err:
                        import logging
                        logging.getLogger(__name__).warning("Could not compute analytics snapshot for imported student %s: %s", student.student_id, eval_err)

                imported_count += 1

        return {"imported_count": imported_count, "errors": errors}

class SyntheticDataGeneratorService:
    """Generates realistic demonstration data for Smart Campus Analytics."""

    @staticmethod
    def generate_all(student_count=40, seed=42):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        with transaction.atomic():
            # 1. Departments & Programs
            departments_data = [
                ('CSE', 'Computer Science & Engineering', 'Dr. Alan Turing'),
                ('ECE', 'Electronics & Communication', 'Dr. Claude Shannon'),
                ('EEE', 'Electrical & Electronics', 'Dr. Nikola Tesla'),
                ('MECH', 'Mechanical Engineering', 'Dr. James Watt')
            ]
            departments = []
            for code, name, hod in departments_data:
                dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name, 'head_of_department': hod})
                departments.append(dept)
                Program.objects.get_or_create(code=f"BTECH-{code}", defaults={'name': f"B.Tech in {name}", 'department': dept})

            # 2. Academic Year & Semesters
            acad_year, _ = AcademicYear.objects.get_or_create(year_label="2025-2026", defaults={'is_current': True})
            semesters = []
            for num in range(1, 9):
                s, _ = Semester.objects.get_or_create(number=num, academic_year=acad_year, defaults={'is_active': (num == 5)})
                semesters.append(s)
            current_sem = semesters[4]  # Sem 5

            # 3. Create Demo Users & Roles
            admin_user, _ = User.objects.get_or_create(
                username='admin',
                defaults={'email': 'admin@smartcampus.edu', 'role': User.Role.ADMINISTRATOR, 'is_staff': True, 'is_superuser': True}
            )
            admin_user.set_password('Admin@1234')
            admin_user.save()

            faculty_user, _ = User.objects.get_or_create(
                username='faculty_cse',
                defaults={'email': 'faculty@smartcampus.edu', 'role': User.Role.FACULTY, 'department_name': 'CSE', 'is_staff': True}
            )
            faculty_user.set_password('Faculty@1234')
            faculty_user.save()
            FacultyAssignment.objects.get_or_create(faculty_user=faculty_user, department=departments[0])

            placement_user, _ = User.objects.get_or_create(
                username='placement_officer',
                defaults={'email': 'placement@smartcampus.edu', 'role': User.Role.PLACEMENT_OFFICER, 'is_staff': True}
            )
            placement_user.set_password('Placement@1234')
            placement_user.save()

            # 4. Subjects
            subjects = []
            for dept in departments:
                sub1, _ = Subject.objects.get_or_create(code=f"{dept.code}301", defaults={'name': f"Advanced {dept.name} Concepts", 'department': dept, 'credits': 4})
                sub2, _ = Subject.objects.get_or_create(code=f"{dept.code}302", defaults={'name': f"{dept.name} Lab & Projects", 'department': dept, 'credits': 3})
                subjects.extend([sub1, sub2])

            # 5. Skills & Categories
            tech_skill1, _ = Skill.objects.get_or_create(name="Python & Machine Learning", category=Skill.SkillCategory.TECHNICAL)
            tech_skill2, _ = Skill.objects.get_or_create(name="Data Structures & Algorithms", category=Skill.SkillCategory.TECHNICAL)
            soft_skill, _ = Skill.objects.get_or_create(name="Leadership & Public Speaking", category=Skill.SkillCategory.SOFT_SKILL)

            act_cat, _ = ActivityCategory.objects.get_or_create(name="Hackathon & Innovation")
            act, _ = EngagementActivity.objects.get_or_create(title="Smart Campus AI Hackathon", defaults={'category': act_cat, 'event_date': date.today() - timedelta(days=20), 'organizer': 'AI Club'})

            fb_cat, _ = FeedbackCategory.objects.get_or_create(name="Academic Support & Infrastructure")

            # 6. Generate Synthetic Students across Groups A-F
            first_names = ['Aarav', 'Ananya', 'Rohan', 'Priya', 'Vikram', 'Sneha', 'Aditya', 'Kavya', 'Rahul', 'Divya', 'Siddharth', 'Meera']
            last_names = ['Sharma', 'Verma', 'Patel', 'Rao', 'Nair', 'Singh', 'Gupta', 'Iyer', 'Reddy', 'Joshi']

            created_students = []
            group_cycle = ['GROUP_A', 'GROUP_B', 'GROUP_C', 'GROUP_D', 'GROUP_E', 'GROUP_F']

            for i in range(1, student_count + 1):
                stu_id = f"STU2025{i:03d}"
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                dept = departments[(i - 1) % len(departments)]
                prog = dept.programs.first()
                group = group_cycle[(i - 1) % len(group_cycle)]

                stu_user, _ = User.objects.get_or_create(
                    username=stu_id.lower(),
                    defaults={'email': f"{stu_id.lower()}@smartcampus.edu", 'first_name': fn, 'last_name': ln, 'role': User.Role.STUDENT}
                )
                stu_user.set_password('Student@1234')
                stu_user.save()

                student, _ = StudentProfile.objects.get_or_create(
                    student_id=stu_id,
                    defaults={
                        'user': stu_user,
                        'first_name': fn,
                        'last_name': ln,
                        'email': stu_user.email,
                        'department': dept,
                        'program': prog,
                        'current_semester': 5,
                        'admission_year': 2023,
                    }
                )
                created_students.append(student)

                # Configure metrics by group
                if group == 'GROUP_A':  # Strong Overall
                    cgpa = round(random.uniform(8.6, 9.8), 2)
                    backlogs = 0
                    att_pct = random.randint(88, 98)
                    lms_completion = random.uniform(88.0, 100.0)
                    plac_score = random.uniform(85.0, 95.0)
                elif group == 'GROUP_B':  # Academic & Attendance Risk
                    cgpa = round(random.uniform(4.5, 6.2), 2)
                    backlogs = random.choice([1, 2, 3])
                    att_pct = random.randint(52, 69)
                    lms_completion = random.uniform(40.0, 62.0)
                    plac_score = random.uniform(35.0, 55.0)
                elif group == 'GROUP_C':  # Strong Academics, Low Placement
                    cgpa = round(random.uniform(8.2, 9.5), 2)
                    backlogs = 0
                    att_pct = random.randint(85, 95)
                    lms_completion = random.uniform(80.0, 95.0)
                    plac_score = random.uniform(35.0, 52.0)  # Weak coding/aptitude
                elif group == 'GROUP_D':  # Low LMS Engagement
                    cgpa = round(random.uniform(7.0, 8.2), 2)
                    backlogs = 0
                    att_pct = random.randint(78, 88)
                    lms_completion = random.uniform(30.0, 48.0)
                    plac_score = random.uniform(65.0, 78.0)
                elif group == 'GROUP_E':  # Incomplete / Missing Records
                    cgpa = round(random.uniform(6.8, 8.0), 2)
                    backlogs = 0
                    att_pct = random.randint(75, 85)
                    lms_completion = 70.0
                    plac_score = None  # No placement record
                else:  # GROUP_F: Improving Students
                    cgpa = round(random.uniform(7.2, 8.4), 2)
                    backlogs = 0
                    att_pct = random.randint(82, 92)
                    lms_completion = random.uniform(75.0, 90.0)
                    plac_score = random.uniform(70.0, 85.0)

                SemesterResult.objects.update_or_create(
                    student=student,
                    semester=current_sem,
                    defaults={
                        'sgpa': cgpa,
                        'cgpa': cgpa,
                        'backlog_count': backlogs,
                        'passed': (backlogs == 0)
                    }
                )

                # Subject Assessments
                dept_subjects = Subject.objects.filter(department=dept)
                for sub in dept_subjects:
                    AssessmentResult.objects.update_or_create(
                        student=student,
                        subject=sub,
                        semester=current_sem,
                        assessment_name="Midterm Exam",
                        defaults={
                            'marks_obtained': round((cgpa / 10.0) * 100 * random.uniform(0.9, 1.05), 2),
                            'max_marks': 100.00
                        }
                    )

                # Attendance Record
                AttendanceRecord.objects.update_or_create(
                    student=student,
                    semester=current_sem,
                    subject=None,
                    defaults={
                        'total_classes': 120,
                        'classes_attended': int((att_pct / 100.0) * 120)
                    }
                )

                # LMS Summary
                LMSActivitySummary.objects.update_or_create(
                    student=student,
                    defaults={
                        'login_frequency': int(att_pct / 4),
                        'assignment_completion_pct': lms_completion,
                        'assignment_timeliness_pct': max(0.0, lms_completion - random.uniform(0, 10)),
                        'learning_resource_views': random.randint(20, 150),
                        'quiz_participation_pct': lms_completion,
                        'last_activity_date': timezone.now() - timedelta(days=random.randint(0, 5))
                    }
                )

                # Placement Assessment (if applicable)
                if plac_score is not None:
                    PlacementAssessment.objects.update_or_create(
                        student=student,
                        defaults={
                            'aptitude_score': round(plac_score * random.uniform(0.9, 1.1), 1),
                            'coding_score': round(plac_score * random.uniform(0.85, 1.15), 1),
                            'mock_interview_score': round(plac_score * random.uniform(0.9, 1.0), 1),
                            'resume_readiness_score': round(random.uniform(60, 95), 1),
                            'communication_score': round(random.uniform(65, 90), 1)
                        }
                    )
                    StudentSkillAssessment.objects.update_or_create(
                        student=student, skill=tech_skill1, defaults={'proficiency_score': plac_score}
                    )
                
                StudentSkillAssessment.objects.update_or_create(
                    student=student, skill=soft_skill, defaults={'proficiency_score': random.uniform(60, 90)}
                )

                # Engagement
                StudentEngagement.objects.update_or_create(
                    student=student, activity=act, defaults={'role': 'Participant', 'engagement_score': random.uniform(50, 90)}
                )

                # Feedback
                StudentFeedback.objects.update_or_create(
                    student=student, category=fb_cat, defaults={'satisfaction_score': random.randint(3, 5), 'comments': 'Great learning environment.'}
                )

                # Evaluate Explainable AI Success Snapshot & Risk Level
                from apps.analytics.services import StudentAnalyticsEngine
                StudentAnalyticsEngine.evaluate_and_save_snapshot(student)

            return len(created_students)
