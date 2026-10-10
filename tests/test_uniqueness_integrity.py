import io
from datetime import date
from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile
from apps.academics.models import Subject, AssessmentResult
from apps.attendance.models import AttendanceRecord
from apps.placements.models import PlacementAssessment, PlacementApplication
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.risk_checker import CSVRiskCheckerService
from apps.feedback.models import FeedbackCategory, StudentFeedback
from apps.engagement.models import ActivityCategory, EngagementActivity


class UniquenessIntegrityTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code="CSE", name="Computer Science")
        self.prog = Program.objects.create(code="BTECH-CSE", name="B.Tech CSE", department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label="2025-2026")
        self.semester = Semester.objects.create(number=1, academic_year=self.acad_year)
        self.student = StudentProfile.objects.create(
            student_id="STU_UNIQ_01",
            first_name="Unique",
            last_name="Tester",
            email="unique.tester@campus.edu",
            department=self.dept,
            program=self.prog,
            admission_year=2024,
            current_semester=1,
        )
        self.subject = Subject.objects.create(code="CS101", name="Intro to CS", department=self.dept)

    def test_attendance_subject_level_uniqueness(self):
        AttendanceRecord.objects.create(
            student=self.student,
            semester=self.semester,
            subject=self.subject,
            total_classes=20,
            classes_attended=18,
        )
        with self.assertRaises(IntegrityError):
            AttendanceRecord.objects.create(
                student=self.student,
                semester=self.semester,
                subject=self.subject,
                total_classes=20,
                classes_attended=15,
            )

    def test_attendance_overall_level_uniqueness(self):
        AttendanceRecord.objects.create(
            student=self.student,
            semester=self.semester,
            subject=None,
            total_classes=100,
            classes_attended=90,
        )
        with self.assertRaises(IntegrityError):
            AttendanceRecord.objects.create(
                student=self.student,
                semester=self.semester,
                subject=None,
                total_classes=100,
                classes_attended=85,
            )

    def test_placement_assessment_uniqueness_per_student(self):
        PlacementAssessment.objects.create(
            student=self.student,
            aptitude_score=75.0,
            coding_score=80.0,
        )
        with self.assertRaises(IntegrityError):
            PlacementAssessment.objects.create(
                student=self.student,
                aptitude_score=60.0,
                coding_score=65.0,
            )

    def test_placement_application_uniqueness(self):
        PlacementApplication.objects.create(
            student=self.student,
            company_name="Acme Corp",
            role_offered="Software Engineer",
        )
        with self.assertRaises(IntegrityError):
            PlacementApplication.objects.create(
                student=self.student,
                company_name="Acme Corp",
                role_offered="Software Engineer",
            )

    def test_student_success_snapshot_uniqueness_per_date(self):
        today = timezone.localdate()
        StudentSuccessSnapshot.objects.create(
            student=self.student,
            overall_success_score=85.0,
            academic_risk_level=StudentSuccessSnapshot.RiskLevel.LOW,
        )
        with self.assertRaises(IntegrityError):
            StudentSuccessSnapshot.objects.create(
                student=self.student,
                overall_success_score=70.0,
                academic_risk_level=StudentSuccessSnapshot.RiskLevel.MEDIUM,
            )

    def test_student_feedback_uniqueness_per_category(self):
        cat = FeedbackCategory.objects.create(name="Campus Infrastructure")
        StudentFeedback.objects.create(
            student=self.student,
            category=cat,
            satisfaction_score=4,
        )
        with self.assertRaises(IntegrityError):
            StudentFeedback.objects.create(
                student=self.student,
                category=cat,
                satisfaction_score=2,
            )

    def test_assessment_result_uniqueness(self):
        AssessmentResult.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.semester,
            assessment_name="Midterm Exam",
            marks_obtained=45.0,
            max_marks=50.0,
        )
        with self.assertRaises(IntegrityError):
            AssessmentResult.objects.create(
                student=self.student,
                subject=self.subject,
                semester=self.semester,
                assessment_name="Midterm Exam",
                marks_obtained=40.0,
                max_marks=50.0,
            )

    def test_engagement_activity_uniqueness(self):
        cat = ActivityCategory.objects.create(name="Clubs")
        event_d = date(2026, 4, 15)
        EngagementActivity.objects.create(
            title="Coding Marathon",
            category=cat,
            event_date=event_d,
        )
        with self.assertRaises(IntegrityError):
            EngagementActivity.objects.create(
                title="Coding Marathon",
                category=cat,
                event_date=event_d,
            )

    def test_csv_risk_checker_rejects_duplicate_student_id_rows(self):
        csv_data = (
            "student_id,name,department,semester,cgpa,attendance_percentage\n"
            "STU999,First Entry,CSE,5,8.5,90.0\n"
            "STU999,Duplicate Entry,CSE,5,6.0,70.0\n"
        )
        buffer = io.BytesIO(csv_data.encode("utf-8"))
        result = CSVRiskCheckerService.analyze_file(buffer, filename="duplicates.csv")

        self.assertEqual(result["total_rows"], 2)
        self.assertEqual(result["valid_rows"], 1)
        self.assertEqual(len(result["records"]), 1)
        self.assertTrue(any("Duplicate student_id" in err for err in result["errors"]))
