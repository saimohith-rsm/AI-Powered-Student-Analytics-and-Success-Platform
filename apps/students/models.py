from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Department(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Department Code, e.g., CSE")
    name = models.CharField(max_length=150, help_text="Department Name, e.g., Computer Science & Engineering")
    head_of_department = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Program(models.Model):
    code = models.CharField(max_length=30, unique=True, help_text="Program Code, e.g., BTECH-CSE")
    name = models.CharField(max_length=150, help_text="Program Name, e.g., Bachelor of Technology in CSE")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    degree_level = models.CharField(max_length=50, default='Undergraduate')

    def __str__(self):
        return f"{self.code} ({self.name})"

class AcademicYear(models.Model):
    year_label = models.CharField(max_length=20, unique=True, help_text="e.g., 2025-2026")
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.year_label

class Semester(models.Model):
    number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Semester Number (1 to 12)"
    )
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='semesters')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('number', 'academic_year')
        ordering = ['academic_year', 'number']

    def __str__(self):
        return f"Semester {self.number} ({self.academic_year.year_label})"

class StudentProfile(models.Model):
    class EnrollmentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        GRADUATED = 'GRADUATED', 'Graduated'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile'
    )
    student_id = models.CharField(max_length=50, unique=True, db_index=True, help_text="Unique Institutional Student ID")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='students')
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name='students')
    current_semester = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)], default=1)
    admission_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    graduation_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)], null=True, blank=True)
    enrollment_status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE
    )

    class Meta:
        ordering = ['student_id']

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.student_id} - {self.full_name} ({self.department.code})"

class FacultyAssignment(models.Model):
    faculty_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_assignments')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='assigned_faculty')
    assigned_date = models.DateField(auto_now_add=True)
    assignment_notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('faculty_user', 'department')

    def __str__(self):
        return f"{self.faculty_user.username} -> {self.department.code}"
