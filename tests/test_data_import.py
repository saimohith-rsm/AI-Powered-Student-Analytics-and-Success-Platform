import csv
import tempfile
from pathlib import Path

from django.test import TestCase

from apps.analytics.models import StudentSuccessSnapshot
from apps.attendance.models import AttendanceRecord
from apps.lms.models import LMSActivitySummary
from apps.placements.models import PlacementAssessment
from apps.students.models import StudentProfile
from apps.skills.models import StudentSkillAssessment
from apps.engagement.models import StudentEngagement
from apps.feedback.models import StudentFeedback
from apps.students.services import DataImportService
from apps.academics.models import SemesterResult


class DataImportServiceTests(TestCase):
    def _csv_file(self, rows, columns):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf-8", delete=False)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        handle.close()
        return handle.name

    def test_missing_domains_are_not_fabricated_during_import(self):
        path = self._csv_file(
            [{"student_id": "IMPORT001", "name": "Test Student"}],
            ["student_id", "name"],
        )
        result = DataImportService.import_from_file(path)

        self.assertEqual(result["imported_count"], 1)
        student = StudentProfile.objects.get(student_id="IMPORT001")
        self.assertFalse(SemesterResult.objects.filter(student=student).exists())
        self.assertFalse(AttendanceRecord.objects.filter(student=student).exists())
        self.assertFalse(LMSActivitySummary.objects.filter(student=student).exists())
        self.assertFalse(PlacementAssessment.objects.filter(student=student).exists())
        snapshot = StudentSuccessSnapshot.objects.filter(student=student).first()
        self.assertIsNone(snapshot)

    def test_invalid_numeric_row_is_skipped_with_validation_error(self):
        path = self._csv_file(
            [{"student_id": "IMPORT002", "name": "Bad CGPA", "cgpa": "not-a-number"}],
            ["student_id", "name", "cgpa"],
        )
        result = DataImportService.import_from_file(path)

        self.assertEqual(result["imported_count"], 0)
        self.assertTrue(any("cgpa" in error for error in result["errors"]))
        self.assertFalse(StudentProfile.objects.filter(student_id="IMPORT002").exists())

    def test_imported_placement_assessment_populates_all_components(self):
        path = self._csv_file(
            [{
                "student_id": "IMPORT003", "name": "Placement Student", "aptitude_score": "80",
                "coding_score": "70", "mock_interview_score": "75",
            }],
            ["student_id", "name", "aptitude_score", "coding_score", "mock_interview_score"],
        )
        result = DataImportService.import_from_file(path)

        self.assertEqual(result["imported_count"], 1)
        assessment = PlacementAssessment.objects.get(student__student_id="IMPORT003")
        self.assertEqual(assessment.resume_readiness_score, 65.0)
        self.assertEqual(assessment.communication_score, 65.0)
        self.assertGreater(assessment.overall_readiness_score, 0)

    def test_import_populates_optional_engagement_skills_and_feedback_domains(self):
        path = self._csv_file(
            [{
                "student_id": "IMPORT004", "name": "All Domains", "engagement_score": "82",
                "technical_skill_score": "78", "soft_skill_score": "85", "feedback_score": "4",
            }],
            ["student_id", "name", "engagement_score", "technical_skill_score", "soft_skill_score", "feedback_score"],
        )
        result = DataImportService.import_from_file(path)
        self.assertEqual(result["imported_count"], 1)
        student = StudentProfile.objects.get(student_id="IMPORT004")
        self.assertTrue(StudentEngagement.objects.filter(student=student, engagement_score=82).exists())
        self.assertEqual(StudentSkillAssessment.objects.filter(student=student).count(), 2)
        self.assertTrue(StudentFeedback.objects.filter(student=student, satisfaction_score=4).exists())

    def test_get_upload_temp_dir_fallback_when_media_root_read_only(self):
        from unittest.mock import patch
        from config.storage_utils import get_upload_temp_dir

        with patch("config.storage_utils.settings") as mock_settings:
            # Simulate unwritable /var/task/media
            mock_settings.MEDIA_ROOT = "/var/task/media_non_writable_test"
            temp_dir = get_upload_temp_dir("imports")
            self.assertTrue(temp_dir.exists())
            self.assertNotEqual(str(temp_dir), "/var/task/media_non_writable_test/imports")

    def test_data_import_web_upload_view_works_with_unwritable_media_root(self):
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse
        from apps.accounts.models import User

        admin_user = User.objects.create_user(
            username='admin_import_tester',
            password='Password@123',
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_superuser=True
        )
        self.client.force_login(admin_user)
        csv_content = b"student_id,name\nSTU_TMP_99,Temp Upload Student\n"
        uploaded = SimpleUploadedFile("temp_roster.csv", csv_content, content_type="text/csv")

        with patch("django.conf.settings.MEDIA_ROOT", "/var/task/media"):
            resp = self.client.post(reverse("students:data_import"), {"dataset_file": uploaded})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.context["import_completed"])
            self.assertEqual(resp.context["imported_count"], 1)
            self.assertTrue(StudentProfile.objects.filter(student_id="STU_TMP_99").exists())

    def test_import_with_full_department_names_and_column_synonyms(self):
        csv_text = (
            "student_id,name,department,semester,cgpa,attendance,backlogs,lms_completion,coding_score\n"
            "CS2023801,Alok Nath,Computer Science & Engineering,4,9.15,92.5,0,95,82\n"
            "CS2023802,Bhavna Menon,Computer Science & Engineering,4,5.6,62,2,45,38\n"
            "IT2023803,Chirag Deshmukh,Information Technology,4,8.4,68,0,82,75\n"
            "EC2022804,Deepa Varma,Electronics & Communication,6,8.75,88,0,90,44\n"
            "ME2023805,Farhan Zaidi,Mechanical Engineering,4,6.95,78.5,0,70,55\n"
        )
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", newline="", encoding="utf-8", delete=False)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        handle.write(csv_text)
        handle.close()

        result = DataImportService.import_from_file(handle.name)
        self.assertEqual(result["imported_count"], 5)
        self.assertEqual(len(result["errors"]), 0)

        # Check resolved department codes
        s1 = StudentProfile.objects.get(student_id="CS2023801")
        self.assertEqual(s1.department.code, "CSE")
        s3 = StudentProfile.objects.get(student_id="IT2023803")
        self.assertEqual(s3.department.code, "IT")
        s4 = StudentProfile.objects.get(student_id="EC2022804")
        self.assertEqual(s4.department.code, "ECE")
        s5 = StudentProfile.objects.get(student_id="ME2023805")
        self.assertEqual(s5.department.code, "MECH")

    def test_duplicate_student_id_in_file_is_rejected(self):
        rows = [
            {"student_id": "DUP001", "name": "First Student", "email": "first@campus.edu"},
            {"student_id": "DUP001", "name": "Duplicate Student", "email": "duplicate@campus.edu"},
        ]
        path = self._csv_file(rows, ["student_id", "name", "email"])
        result = DataImportService.import_from_file(path)

        # Only the first student should be imported, the duplicate must be flagged in errors
        self.assertEqual(result["imported_count"], 1)
        self.assertTrue(any("Duplicate student_id" in err for err in result["errors"]))
        self.assertEqual(StudentProfile.objects.filter(student_id="DUP001").count(), 1)
        self.assertEqual(StudentProfile.objects.get(student_id="DUP001").first_name, "First")

    def test_duplicate_email_in_file_is_rejected(self):
        rows = [
            {"student_id": "EMAIL001", "name": "Student One", "email": "shared@campus.edu"},
            {"student_id": "EMAIL002", "name": "Student Two", "email": "shared@campus.edu"},
        ]
        path = self._csv_file(rows, ["student_id", "name", "email"])
        result = DataImportService.import_from_file(path)

        self.assertEqual(result["imported_count"], 1)
        self.assertTrue(any("Duplicate email" in err for err in result["errors"]))
        self.assertEqual(StudentProfile.objects.filter(email="shared@campus.edu").count(), 1)

