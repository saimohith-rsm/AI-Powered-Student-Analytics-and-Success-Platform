from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.services import StudentAnalyticsEngine
from apps.interventions.models import InterventionRecord

User = get_user_model()

class Part3DashboardTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Institutional Base
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(code='BTECH-CSE', name='B.Tech CSE', department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label='2025-2026', is_current=True)
        self.sem = Semester.objects.create(number=5, academic_year=self.acad_year)

        # Users
        self.admin = User.objects.create_user(username='admin_user', password='Password123', role=User.Role.ADMINISTRATOR, is_staff=True, is_superuser=True)
        self.faculty = User.objects.create_user(username='faculty_user', password='Password123', role=User.Role.FACULTY, department_name='CSE')
        self.student_user = User.objects.create_user(username='student_user', password='Password123', role=User.Role.STUDENT)

        # Student Profile
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id='STU3001',
            first_name='John',
            last_name='Dashboard',
            email='john.dashboard@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=5,
            admission_year=2023
        )
        StudentAnalyticsEngine.evaluate_and_save_snapshot(self.student)

    def test_overview_dashboard_rendering(self):
        self.client.login(username='admin_user', password='Password123')
        response = self.client.get(reverse('analytics:overview_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_enrolled', response.context)
        self.assertIn('dept_summary', response.context)

    def test_student_directory_search_and_filter(self):
        self.client.login(username='faculty_user', password='Password123')
        response = self.client.get(reverse('analytics:student_directory') + '?q=John')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['students']), 1)

    def test_student_detail_view(self):
        self.client.login(username='faculty_user', password='Password123')
        response = self.client.get(reverse('analytics:student_detail', kwargs={'student_id': 'STU3001'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'].student_id, 'STU3001')

    def test_student_role_isolation_on_detail_view(self):
        # Create student 2
        u2 = User.objects.create_user(username='other_student', password='Password123', role=User.Role.STUDENT)
        s2 = StudentProfile.objects.create(user=u2, student_id='STU3002', first_name='Other', last_name='Student', email='other@campus.edu', department=self.dept, program=self.prog, current_semester=5, admission_year=2023)

        # Login as student 1 and try to access student 2 detail page
        self.client.login(username='student_user', password='Password123')
        response = self.client.get(reverse('analytics:student_detail', kwargs={'student_id': 'STU3002'}))
        self.assertEqual(response.status_code, 403)

    def test_intervention_action_creation_and_update(self):
        self.client.login(username='faculty_user', password='Password123')
        # Create
        post_resp = self.client.post(reverse('analytics:intervention_action'), {
            'student_id': 'STU3001',
            'intervention_type': 'ACADEMIC_TUTORING',
            'reason': 'Low midterms mark',
            'status': 'PROPOSED'
        })
        self.assertEqual(post_resp.status_code, 302)
        interv = InterventionRecord.objects.filter(student=self.student).first()
        self.assertIsNotNone(interv)

        # Update
        update_resp = self.client.post(reverse('analytics:intervention_action'), {
            'intervention_id': interv.id,
            'status': 'COMPLETED',
            'outcome_notes': 'Tutoring sessions finished successfully.'
        })
        self.assertEqual(update_resp.status_code, 302)
        interv.refresh_from_db()
        self.assertEqual(interv.status, 'COMPLETED')

    def test_report_csv_export_permissions(self):
        self.client.login(username='admin_user', password='Password123')
        response = self.client.get(reverse('analytics:export_report', kwargs={'report_type': 'risk'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # Student try to export -> 403
        self.client.login(username='student_user', password='Password123')
        stu_resp = self.client.get(reverse('analytics:export_report', kwargs={'report_type': 'risk'}))
        self.assertEqual(stu_resp.status_code, 403)
