from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.students.models import Department, Program, AcademicYear, Semester, StudentProfile
from apps.academics.models import Subject, SemesterResult, AssessmentResult
from apps.attendance.models import AttendanceRecord
from apps.accounts.permissions import role_required

User = get_user_model()

class SmartCampusFoundationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Baseline Department and Program
        self.dept = Department.objects.create(code='CSE', name='Computer Science & Engineering')
        self.prog = Program.objects.create(code='BTECH-CSE', name='B.Tech CSE', department=self.dept)
        self.acad_year = AcademicYear.objects.create(year_label='2025-2026', is_current=True)
        self.sem = Semester.objects.create(number=1, academic_year=self.acad_year)

        # Create Users for Roles
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='Password123',
            role=User.Role.ADMINISTRATOR,
            is_staff=True
        )
        self.faculty_user = User.objects.create_user(
            username='faculty_test',
            email='faculty@test.com',
            password='Password123',
            role=User.Role.FACULTY
        )
        self.student_user = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='Password123',
            role=User.Role.STUDENT
        )

        # Create Student Profile
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            student_id='STU2025001',
            first_name='Test',
            last_name='Student',
            email='teststudent@campus.edu',
            department=self.dept,
            program=self.prog,
            current_semester=1,
            admission_year=2025
        )

    def test_user_creation_and_roles(self):
        self.assertTrue(self.admin_user.is_admin_user())
        self.assertTrue(self.faculty_user.is_faculty_user())
        self.assertTrue(self.student_user.is_student_user())
        self.assertFalse(self.student_user.is_admin_user())

    def test_duplicate_student_id_raises_error(self):
        with self.assertRaises(IntegrityError):
            StudentProfile.objects.create(
                student_id='STU2025001',  # Duplicate ID
                first_name='Duplicate',
                last_name='User',
                email='duplicate@campus.edu',
                department=self.dept,
                program=self.prog,
                current_semester=1,
                admission_year=2025
            )

    def test_invalid_cgpa_validation(self):
        result = SemesterResult(
            student=self.student,
            semester=self.sem,
            sgpa=11.5,  # Invalid SGPA > 10.0
            cgpa=12.0   # Invalid CGPA > 10.0
        )
        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_invalid_attendance_validation(self):
        record = AttendanceRecord(
            student=self.student,
            semester=self.sem,
            total_classes=10,
            classes_attended=15  # Impossible: attended > total
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_invalid_assessment_marks_validation(self):
        subject = Subject.objects.create(code='CS101', name='Intro to CS', department=self.dept, credits=3)
        assessment = AssessmentResult(
            student=self.student,
            subject=subject,
            semester=self.sem,
            assessment_name='Midterm',
            marks_obtained=110.0,
            max_marks=100.0  # Impossible: marks_obtained > max_marks
        )
        with self.assertRaises(ValidationError):
            assessment.full_clean()

    def test_page_rendering(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)

        login_response = self.client.get(reverse('accounts:login'))
        self.assertEqual(login_response.status_code, 200)

    def test_dashboard_redirection_by_role(self):
        # Admin Login -> Executive Overview Dashboard
        self.client.login(username='admin_test', password='Password123')
        resp = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(resp, reverse('analytics:overview_dashboard'))

        # Student Login -> Personal Student Profile
        self.client.login(username='student_test', password='Password123')
        resp_stu = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(resp_stu, reverse('analytics:student_detail', kwargs={'student_id': self.student.student_id}))
