from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile
from apps.academics.models import SemesterResult
from apps.attendance.models import AttendanceRecord
from apps.lms.models import LMSActivitySummary
from apps.placements.models import PlacementAssessment
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.services import StudentAnalyticsEngine
from apps.interventions.models import InterventionRecord

User = get_user_model()

class Part4IntegrationScenariosTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Department setup
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(code='BTECH-CSE', name='B.Tech CSE', department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label='2025-2026', is_current=True)
        self.sem = Semester.objects.create(number=5, academic_year=self.acad_year)

        # Users
        self.admin = User.objects.create_user(username='admin_s1', password='Password123', role=User.Role.ADMINISTRATOR, is_staff=True, is_superuser=True)
        self.faculty = User.objects.create_user(username='faculty_s2', password='Password123', role=User.Role.FACULTY, department_name='CSE')
        self.placement = User.objects.create_user(username='placement_s3', password='Password123', role=User.Role.PLACEMENT_OFFICER)
        self.student_u1 = User.objects.create_user(username='student_s4', password='Password123', role=User.Role.STUDENT)

        # Student Profile
        self.student = StudentProfile.objects.create(
            user=self.student_u1,
            student_id='STU4001',
            first_name='Scenario',
            last_name='Tester',
            email='scenario@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=5,
            admission_year=2023
        )
        SemesterResult.objects.create(student=self.student, semester=self.sem, sgpa=8.5, cgpa=8.5, backlog_count=0)
        AttendanceRecord.objects.create(student=self.student, semester=self.sem, subject=None, total_classes=100, classes_attended=90)
        LMSActivitySummary.objects.create(student=self.student, login_frequency=20, assignment_completion_pct=90.0, assignment_timeliness_pct=90.0)

    def test_scenario1_admin_workflow(self):
        self.client.login(username='admin_s1', password='Password123')
        resp = self.client.get(reverse('analytics:overview_dashboard'))
        self.assertEqual(resp.status_code, 200)

        import_resp = self.client.get(reverse('students:data_import'))
        self.assertEqual(import_resp.status_code, 200)

    def test_scenario2_faculty_workflow(self):
        self.client.login(username='faculty_s2', password='Password123')
        resp = self.client.get(reverse('analytics:student_directory'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['students']), 1)

    def test_scenario3_placement_officer_workflow(self):
        self.client.login(username='placement_s3', password='Password123')
        resp = self.client.get(reverse('analytics:overview_dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_scenario4_student_isolation(self):
        self.client.login(username='student_s4', password='Password123')
        resp = self.client.get(reverse('analytics:student_detail', kwargs={'student_id': 'STU4001'}))
        self.assertEqual(resp.status_code, 200)

    def test_scenario5_missing_data_handling(self):
        # Student has NO placement assessment created
        snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(self.student)
        self.assertIsNotNone(snapshot)
        self.assertGreater(snapshot.overall_success_score, 0.0)

    def test_scenario6_risky_student_workflow(self):
        # Create Risky Student
        u_risk = User.objects.create_user(username='risky_student', password='Password123', role=User.Role.STUDENT)
        s_risk = StudentProfile.objects.create(user=u_risk, student_id='STU4002', first_name='Risky', last_name='Student', email='risky@campus.edu', department=self.dept, program=self.prog, current_semester=5, admission_year=2023)
        SemesterResult.objects.create(student=s_risk, semester=self.sem, sgpa=4.5, cgpa=4.8, backlog_count=3)
        AttendanceRecord.objects.create(student=s_risk, semester=self.sem, subject=None, total_classes=100, classes_attended=55)

        snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(s_risk)
        self.assertIn(snapshot.academic_risk_level, ['HIGH', 'CRITICAL'])

    def test_scenario7_strong_academics_low_placement(self):
        # Student with CGPA 9.2 but low placement score (45.0)
        u_c = User.objects.create_user(username='group_c_student', password='Password123', role=User.Role.STUDENT)
        s_c = StudentProfile.objects.create(user=u_c, student_id='STU4003', first_name='GroupC', last_name='Student', email='groupc@campus.edu', department=self.dept, program=self.prog, current_semester=5, admission_year=2023)
        SemesterResult.objects.create(student=s_c, semester=self.sem, sgpa=9.2, cgpa=9.2, backlog_count=0)
        AttendanceRecord.objects.create(student=s_c, semester=self.sem, subject=None, total_classes=100, classes_attended=92)
        PlacementAssessment.objects.create(student=s_c, aptitude_score=45.0, coding_score=40.0, mock_interview_score=50.0, resume_readiness_score=45.0, communication_score=50.0)

        snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(s_c)
        self.assertEqual(snapshot.segment, "Placement Support Needed")

    def test_faculty_cannot_view_student_outside_assigned_department(self):
        other_dept = Department.objects.create(code='ECE', name='Electronics')
        other_program = Program.objects.create(code='BTECH-ECE', name='B.Tech ECE', department=other_dept)
        other_user = User.objects.create_user(username='ece_student', password='Password123', role=User.Role.STUDENT)
        other_student = StudentProfile.objects.create(
            user=other_user, student_id='STUECE01', first_name='ECE', last_name='Student',
            email='ece.student@campus.edu', department=other_dept, program=other_program,
            current_semester=1, admission_year=2025,
        )
        self.client.login(username='faculty_s2', password='Password123')
        self.client.raise_request_exception = False
        response = self.client.get(reverse('analytics:student_detail', kwargs={'student_id': other_student.student_id}))
        self.assertEqual(response.status_code, 403)


    def test_recalculation_updates_same_day_snapshot_instead_of_duplicating(self):
        StudentAnalyticsEngine.evaluate_and_save_snapshot(self.student)
        StudentAnalyticsEngine.evaluate_and_save_snapshot(self.student)
        self.assertEqual(StudentSuccessSnapshot.objects.filter(student=self.student).count(), 1)

