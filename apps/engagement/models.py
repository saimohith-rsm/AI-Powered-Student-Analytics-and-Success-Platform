from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import StudentProfile

class ActivityCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Club, Hackathon, Workshop, Certification")

    class Meta:
        verbose_name_plural = "Activity Categories"

    def __str__(self):
        return self.name

class EngagementActivity(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, related_name='activities')
    event_date = models.DateField()
    organizer = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.category.name})"

class StudentEngagement(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='engagement_records')
    activity = models.ForeignKey(EngagementActivity, on_delete=models.CASCADE, related_name='participants')
    role = models.CharField(max_length=100, default='Participant', help_text="e.g. Lead, Participant, Winner")
    engagement_score = models.FloatField(
        default=50.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Calculated engagement metric (0-100)"
    )

    class Meta:
        unique_together = ('student', 'activity')

    def __str__(self):
        return f"{self.student.student_id} - {self.activity.title} ({self.role})"
