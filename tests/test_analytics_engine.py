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

class StudentAnalyticsEngineTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Institutional Setup
        self.dept = Department.objects.create(code='CSE', name='Computer Science')
        self.prog = Program.objects.create(code='BTECH-CSE', name='B.Tech CSE', department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label='2025-2026', is_current=True)
        self.sem = Semester.objects.create(number=5, academic_year=self.acad_year)

        # Users
        self.admin = User.objects.create_user(username='admin_test', password='Password123', role=User.Role.ADMINISTRATOR, is_staff=True, is_superuser=True)
        self.student_user1 = User.objects.create_user(username='stu1', password='Password123', role=User.Role.STUDENT)
        self.student_user2 = User.objects.create_user(username='stu2', password='Password123', role=User.Role.STUDENT)

        # Student 1: High Performer
        self.student1 = StudentProfile.objects.create(
            user=self.student_user1,
            student_id='STU001',
            first_name='Alice',
            last_name='High',
            email='alice@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=5,
            admission_year=2023
        )
        SemesterResult.objects.create(student=self.student1, semester=self.sem, sgpa=9.2, cgpa=9.1, backlog_count=0)
        AttendanceRecord.objects.create(student=self.student1, semester=self.sem, subject=None, total_classes=100, classes_attended=95)
        LMSActivitySummary.objects.create(student=self.student1, login_frequency=20, assignment_completion_pct=95.0, assignment_timeliness_pct=95.0)
        PlacementAssessment.objects.create(
            student=self.student1,
            aptitude_score=85.0,
            coding_score=90.0,
            mock_interview_score=88.0,
            resume_readiness_score=85.0,
            communication_score=85.0
        )
        
        # Skill & Engagement for Student 1
        from apps.skills.models import Skill, StudentSkillAssessment
        skill = Skill.objects.create(name="Python", category=Skill.SkillCategory.TECHNICAL)
        StudentSkillAssessment.objects.create(student=self.student1, skill=skill, proficiency_score=90.0)

        # Student 2: Academic & Attendance Risk
        self.student2 = StudentProfile.objects.create(
            user=self.student_user2,
            student_id='STU002',
            first_name='Bob',
            last_name='Risk',
            email='bob@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=5,
            admission_year=2023
        )
        SemesterResult.objects.create(student=self.student2, semester=self.sem, sgpa=5.2, cgpa=5.5, backlog_count=2)
        AttendanceRecord.objects.create(student=self.student2, semester=self.sem, subject=None, total_classes=100, classes_attended=62)
        LMSActivitySummary.objects.create(student=self.student2, login_frequency=5, assignment_completion_pct=45.0, assignment_timeliness_pct=40.0)
        PlacementAssessment.objects.create(student=self.student2, aptitude_score=40.0, coding_score=35.0, mock_interview_score=45.0)

    def test_high_performer_score_and_risk(self):
        metrics = StudentAnalyticsEngine.calculate_student_success_score(self.student1)
        self.assertGreaterEqual(metrics['overall_success_score'], 80.0)
        self.assertEqual(metrics['academic_risk_level'], StudentSuccessSnapshot.RiskLevel.LOW)
        self.assertEqual(metrics['segment'], "High Performing")
        self.assertIn("Outstanding CGPA: 9.10", metrics['explanation_json']['positive_factors'])

    def test_at_risk_score_and_risk(self):
        metrics = StudentAnalyticsEngine.calculate_student_success_score(self.student2)
        self.assertLess(metrics['overall_success_score'], 65.0)
        self.assertIn(metrics['academic_risk_level'], [StudentSuccessSnapshot.RiskLevel.HIGH, StudentSuccessSnapshot.RiskLevel.CRITICAL])
        self.assertTrue(len(metrics['explanation_json']['risk_flags']) >= 2)

    def test_automated_intervention_creation(self):
        InterventionRecord.objects.all().delete()
        snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(self.student2, auto_create_intervention=True)
        self.assertIsNotNone(snapshot)
        
        # Verify Intervention created for Student 2
        intervention = InterventionRecord.objects.filter(student=self.student2).first()
        self.assertIsNotNone(intervention)
        self.assertIn("Automated AI Risk Flag", intervention.reason)

    def test_api_success_score_access_isolation(self):
        # Login as student 1 and try to access student 2 analytics
        self.client.login(username='stu1', password='Password123')
        url = reverse('analytics:api_success_score', kwargs={'student_id': 'STU002'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Access own score
        own_url = reverse('analytics:api_success_score', kwargs={'student_id': 'STU001'})
        own_response = self.client.get(own_url)
        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertIn('overall_success_score', own_response.data)

    def test_api_summary_for_admin(self):
        StudentAnalyticsEngine.evaluate_all_students()
        self.client.login(username='admin_test', password='Password123')
        url = reverse('analytics:api_summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('risk_distribution', response.data)
        self.assertEqual(response.data['total_students'], 2)
