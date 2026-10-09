from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import StudentProfile

class PlacementAssessment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='placement_assessments')
    assessment_date = models.DateField(auto_now_add=True)
    aptitude_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    coding_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    mock_interview_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    resume_readiness_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    communication_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    class Meta:
        ordering = ['-assessment_date']

    @property
    def overall_readiness_score(self):
        scores = [
            self.aptitude_score,
            self.coding_score,
            self.mock_interview_score,
            self.resume_readiness_score,
            self.communication_score
        ]
        return round(sum(scores) / len(scores), 2)

    def __str__(self):
        return f"{self.student.student_id} - Readiness: {self.overall_readiness_score}% ({self.assessment_date})"

class PlacementApplication(models.Model):
    class ApplicationStatus(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        OFFERED = 'OFFERED', 'Offered'
        REJECTED = 'REJECTED', 'Rejected'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='placement_applications')
    company_name = models.CharField(max_length=150)
    role_offered = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.APPLIED)
    package_lpa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Package in LPA (Lakhs Per Annum)")
    applied_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.student_id} -> {self.company_name} ({self.get_status_display()})"
