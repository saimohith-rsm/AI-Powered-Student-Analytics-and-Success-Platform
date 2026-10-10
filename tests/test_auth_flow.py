from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.students.models import Department, Program, StudentProfile

User = get_user_model()

class RegistrationAndLoginFlowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(
            code="CSE",
            name="Computer Science & Engineering"
        )
        self.program = Program.objects.create(
            code="BTECH-CSE",
            name="B.Tech Computer Science",
            department=self.department
        )
        # Seed one existing user for testing login and duplicate checks
        self.existing_username = "existing_testuser"
        self.existing_email = "existing_testuser@campus.edu"
        self.raw_password = "ValidSecurePass123!"
        self.existing_user = User.objects.create_user(
            username=self.existing_username,
            email=self.existing_email,
            password=self.raw_password,
            first_name="Existing",
            last_name="User",
            role=User.Role.STUDENT
        )
        self.existing_profile = StudentProfile.objects.create(
            user=self.existing_user,
            student_id="STU2025999",
            first_name="Existing",
            last_name="User",
            email=self.existing_email,
            department=self.department,
            program=self.program,
            admission_year=2025,
            current_semester=1
        )

    def test_registration_creates_database_records_and_hashes_password(self):
        """Verify that registration creates User & StudentProfile and hashes the password."""
        initial_user_count = User.objects.count()
        initial_profile_count = StudentProfile.objects.count()

        reg_data = {
            'username': 'new_candidate',
            'email': 'new_candidate@campus.edu',
            'password': 'SecureP@ssword2026',
            'first_name': 'Candidate',
            'last_name': 'Student',
            'student_id': 'STU2026101',
            'department': self.department.id,
        }

        response = self.client.post(reverse('accounts:register'), data=reg_data, follow=False)

        # Should redirect to dashboard redirect upon successful registration
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:dashboard_redirect'))

        # Verify database record creation
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        self.assertEqual(StudentProfile.objects.count(), initial_profile_count + 1)

        new_user = User.objects.get(username='new_candidate')
        self.assertEqual(new_user.email, 'new_candidate@campus.edu')
        self.assertEqual(new_user.role, User.Role.STUDENT)
        self.assertTrue(new_user.is_student_user())

        # Verify password is secure hash, NOT plain text
        self.assertNotEqual(new_user.password, reg_data['password'])
        self.assertTrue(new_user.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(new_user.check_password(reg_data['password']))
        self.assertTrue(new_user.has_usable_password())

        # Verify StudentProfile association
        profile = StudentProfile.objects.get(student_id='STU2026101')
        self.assertEqual(profile.user, new_user)
        self.assertEqual(profile.department, self.department)

        # Verify user is logged into session
        self.assertEqual(int(self.client.session['_auth_user_id']), new_user.pk)

    def test_successful_login(self):
        """Verify that a user can log in with valid database credentials."""
        login_url = reverse('accounts:login')
        response = self.client.post(
            login_url,
            {'username': self.existing_username, 'password': self.raw_password},
            follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:dashboard_redirect'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.pk)

    def test_login_fails_with_incorrect_password(self):
        """Verify that login fails and denies access when password does not match."""
        login_url = reverse('accounts:login')
        response = self.client.post(
            login_url,
            {'username': self.existing_username, 'password': 'WrongPassword123!'},
            follow=False
        )
        # Does not redirect; re-renders login form with status 200
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_rejects_duplicate_username(self):
        """Verify that registering with an existing username is rejected."""
        user_count_before = User.objects.count()
        reg_data = {
            'username': self.existing_username,  # Duplicate
            'email': 'different_email@campus.edu',
            'password': 'SecureP@ssword2026',
            'first_name': 'Another',
            'last_name': 'Person',
            'student_id': 'STU2026102',
            'department': self.department.id,
        }
        response = self.client.post(reverse('accounts:register'), data=reg_data, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), user_count_before)

    def test_registration_rejects_duplicate_email(self):
        """Verify that registering with an existing email is rejected."""
        user_count_before = User.objects.count()
        reg_data = {
            'username': 'unique_user_99',
            'email': self.existing_email,  # Duplicate email
            'password': 'SecureP@ssword2026',
            'first_name': 'Another',
            'last_name': 'Person',
            'student_id': 'STU2026103',
            'department': self.department.id,
        }
        response = self.client.post(reverse('accounts:register'), data=reg_data, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), user_count_before)

    def test_registration_rejects_duplicate_student_id(self):
        """Verify that registering with an existing student_id is rejected."""
        user_count_before = User.objects.count()
        reg_data = {
            'username': 'unique_user_100',
            'email': 'unique_email_100@campus.edu',
            'password': 'SecureP@ssword2026',
            'first_name': 'Another',
            'last_name': 'Person',
            'student_id': 'STU2025999',  # Duplicate student ID
            'department': self.department.id,
        }
        response = self.client.post(reverse('accounts:register'), data=reg_data, follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), user_count_before)
