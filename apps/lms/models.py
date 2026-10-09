from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import StudentProfile

class LMSActivitySummary(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='lms_summary')
    login_frequency = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Logins per month")
    last_activity_date = models.DateTimeField(null=True, blank=True)
    assignment_completion_pct = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of assignments submitted (0-100)"
    )
    assignment_timeliness_pct = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of assignments submitted on time (0-100)"
    )
    learning_resource_views = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quiz_participation_pct = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Quiz participation percentage (0-100)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LMS Summary: {self.student.student_id} (Comp: {self.assignment_completion_pct}%)"
