"""Unit and integration tests for the Student Risk Alert Email feature and landing page."""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.alert_service import StudentRiskAlertService
from apps.interventions.models import InterventionRecord

User = get_user_model()


class RiskAlertTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(code='BTECH-CSE', name='B.Tech CSE', department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label='2025-2026', is_current=True)
        self.sem = Semester.objects.create(number=5, academic_year=self.acad_year)

        self.admin = User.objects.create_user(
            username='alert_admin',
            password='Password123',
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_superuser=True,
        )
        self.faculty = User.objects.create_user(
            username='alert_faculty',
            password='Password123',
            role=User.Role.FACULTY,
            department_name='CSE',
        )
        self.student_user = User.objects.create_user(
            username='alert_student',
            password='Password123',
            role=User.Role.STUDENT,
        )

        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id='STU_ALERT_01',
            first_name='Alex',
            last_name='Risk',
            email='alex.risk@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=5,
            admission_year=2023,
        )

        # Baseline snapshot with CRITICAL risk
        self.snapshot = StudentSuccessSnapshot.objects.create(
            student=self.student,
            academic_risk_level='CRITICAL',
            overall_success_score=38.5,
            explanation_json={
                "risk_flags": [
                    "Attendance below critical threshold (64.0%)",
                    "Semester backlogs detected (2 active backlogs)",
                ],
                "positive_factors": [],
            },
        )

    def test_service_sends_individual_alert_email_and_logs_intervention(self):
        mail.outbox.clear()
        InterventionRecord.objects.all().delete()

        result = StudentRiskAlertService.send_individual_alert(
            student=self.student,
            sender_user=self.faculty,
            custom_note="Please meet me during office hours.",
            create_intervention=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["student_id"], "STU_ALERT_01")
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertIn("CRITICAL RISK ALERT", sent_email.subject)
        self.assertIn("STU_ALERT_01", sent_email.subject)
        self.assertEqual(sent_email.to, ["alex.risk@campus.edu"])
        self.assertIn("38.5 / 100", sent_email.body)
        self.assertIn("Attendance below critical threshold", sent_email.body)
        self.assertIn("Please meet me during office hours.", sent_email.body)

        # Verify intervention record was automatically logged
        interventions = InterventionRecord.objects.filter(student=self.student)
        self.assertEqual(interventions.count(), 1)
        self.assertIn("Risk alert email dispatched", interventions.first().reason)

    def test_send_alert_view_permissions(self):
        url = reverse('analytics:send_risk_alert', kwargs={'student_id': self.student.student_id})

        # Student user forbidden (403)
        self.client.force_login(self.student_user)
        resp = self.client.post(url, {'custom_note': 'Attempt from student'})
        self.assertEqual(resp.status_code, 403)

        # Faculty user allowed (302 redirect)
        mail.outbox.clear()
        self.client.force_login(self.faculty)
        resp = self.client.post(url, {'custom_note': 'Counselor notice'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_batch_alerts_view(self):
        url = reverse('analytics:send_batch_risk_alerts')
        mail.outbox.clear()

        self.client.force_login(self.admin)
        resp = self.client.post(url, {'custom_note': 'Department-wide remedial counseling'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_landing_page_displays_alert_and_checker_features(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Smart Campus Analytics & Student Success Platform")
        self.assertContains(response, "Sign In to Portal")
