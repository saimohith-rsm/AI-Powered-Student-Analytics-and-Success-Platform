from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRATOR = 'ADMIN', 'Administrator'
        FACULTY = 'FACULTY', 'Faculty'
        PLACEMENT_OFFICER = 'PLACEMENT', 'Placement Officer'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Role determining application access permissions."
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department_name = models.CharField(max_length=100, blank=True, null=True)

    def is_admin_user(self):
        return self.role == self.Role.ADMINISTRATOR or self.is_superuser

    def is_faculty_user(self):
        return self.role == self.Role.FACULTY or self.is_admin_user()

    def is_placement_officer(self):
        return self.role == self.Role.PLACEMENT_OFFICER or self.is_admin_user()

    def is_student_user(self):
        return self.role == self.Role.STUDENT

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
