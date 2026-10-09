import io
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.analytics.risk_checker import CSVRiskCheckerService
from apps.analytics.models import StudentSuccessSnapshot
from apps.students.models import StudentProfile


class CSVRiskCheckerTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_test',
            password='Password@123',
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_superuser=True
        )
        self.faculty = User.objects.create_user(
            username='faculty_test',
            password='Password@123',
            role=User.Role.FACULTY,
            department_name='CSE',
            is_staff=True
        )
        self.student_user = User.objects.create_user(
            username='student_test',
            password='Password@123',
            role=User.Role.STUDENT
        )
        self.client = Client()

    def test_csv_risk_checker_service_evaluation(self):
        csv_data = (
            "student_id,name,department,semester,cgpa,attendance_percentage,backlog_count,lms_login_frequency,assignment_completion_percentage,coding_score,aptitude_score\n"
            "STU001,High Performer,CSE,5,9.2,95.0,0,30,98.0,90.0,92.0\n"
            "STU002,Critical Risk Student,ECE,5,4.5,55.0,3,5,40.0,30.0,35.0\n"
            "STU003,Attendance Warning Student,MECH,5,7.8,70.0,0,20,85.0,75.0,70.0\n"
        )
        buffer = io.BytesIO(csv_data.encode('utf-8'))
        result = CSVRiskCheckerService.analyze_file(buffer, filename="test_students.csv")

        self.assertEqual(result["total_rows"], 3)
        self.assertEqual(result["valid_rows"], 3)
        self.assertEqual(result["critical_count"], 1)
        self.assertEqual(result["low_count"], 1)

        # STU001 - Low Risk / Safe
        rec1 = result["records"][0]
        self.assertEqual(rec1["student_id"], "STU001")
        self.assertEqual(rec1["risk_level"], "LOW")
        self.assertFalse(rec1["is_at_risk"])
        self.assertGreater(rec1["overall_success_score"], 80)
        self.assertTrue(any("Outstanding CGPA" in f for f in rec1["positive_factors"]))

        # STU002 - Critical Risk
        rec2 = result["records"][1]
        self.assertEqual(rec2["student_id"], "STU002")
        self.assertEqual(rec2["risk_level"], "CRITICAL")
        self.assertTrue(rec2["is_at_risk"])
        self.assertTrue(any("Low CGPA" in f for f in rec2["risk_flags"]))
        self.assertTrue(any("Backlogs" in f for f in rec2["risk_flags"]))
        self.assertTrue(any("Attendance" in f for f in rec2["risk_flags"]))
        self.assertIn("Academic Tutoring", rec2["recommended_interventions"])
        self.assertIn("Attendance Counseling", rec2["recommended_interventions"])

        # STU003 - Attendance deficit triggers High/Medium risk
        rec3 = result["records"][2]
        self.assertEqual(rec3["student_id"], "STU003")
        self.assertTrue(rec3["is_at_risk"])
        self.assertTrue(any("Attendance Deficit" in f for f in rec3["risk_flags"]))

    def test_risk_checker_get_view_requires_staff(self):
        url = reverse('analytics:csv_risk_checker')

        # Anonymous redirect to login
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Student user permission denied (403)
        self.client.force_login(self.student_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Admin user allowed (200)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("column_specs", response.context)
        self.assertIn("canonical_header_csv", response.context)
        self.assertContains(response, "CSV Student Risk Checker & Import")
        self.assertContains(response, "Download Sample CSV")

    def test_risk_checker_preview_mode_does_not_modify_database(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.admin)
        url = reverse('analytics:csv_risk_checker')

        csv_content = b"student_id,name,department,semester,cgpa,attendance_percentage,backlog_count\nPREVIEW01,Preview Student,CSE,5,8.0,90.0,0\n"
        uploaded = SimpleUploadedFile("preview_test.csv", csv_content, content_type="text/csv")

        response = self.client.post(url, {
            'dataset_file': uploaded,
            'action': 'analyze'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['analysis_completed'])
        self.assertFalse(response.context['did_import'])
        self.assertEqual(response.context['results']['valid_rows'], 1)

        # DB must NOT contain student
        self.assertFalse(StudentProfile.objects.filter(student_id="PREVIEW01").exists())

    def test_risk_checker_import_mode_persists_records_and_snapshot(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.admin)
        url = reverse('analytics:csv_risk_checker')

        csv_content = b"student_id,name,department,semester,cgpa,attendance_percentage,backlog_count\nIMPORT01,Saved Student,CSE,5,5.2,65.0,2\n"
        uploaded = SimpleUploadedFile("import_test.csv", csv_content, content_type="text/csv")

        response = self.client.post(url, {
            'dataset_file': uploaded,
            'action': 'import_and_analyze'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['analysis_completed'])
        self.assertTrue(response.context['did_import'])
        self.assertEqual(response.context['imported_count'], 1)

        # Student Profile and StudentSuccessSnapshot must exist in DB
        student = StudentProfile.objects.get(student_id="IMPORT01")
        self.assertEqual(student.full_name, "Saved Student")
        snapshot = StudentSuccessSnapshot.objects.filter(student=student).first()
        self.assertIsNotNone(snapshot)
        self.assertIn(snapshot.academic_risk_level, ["HIGH", "CRITICAL"])

    def test_download_sample_template_view(self):
        self.client.force_login(self.admin)
        url = reverse('analytics:download_sample_template')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="sample_student_import_template.csv"', response['Content-Disposition'])
