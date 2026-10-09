from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import StudentProfile

class FeedbackCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Course Quality, Campus Facilities, Mentorship")

    class Meta:
        verbose_name_plural = "Feedback Categories"

    def __str__(self):
        return self.name

class StudentFeedback(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='submitted_feedback')
    category = models.ForeignKey(FeedbackCategory, on_delete=models.CASCADE, related_name='feedbacks')
    satisfaction_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 (Very Poor) to 5 (Excellent)"
    )
    comments = models.TextField(blank=True, null=True)
    submitted_date = models.DateField(auto_now_add=True)
    is_confidential = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback: {self.student.student_id} -> {self.category.name} ({self.satisfaction_score}/5)"

class FacultyFeedback(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='faculty_feedbacks')
    faculty_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_feedbacks')
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Faculty Observation: {self.faculty_user.username} for {self.student.student_id}"
