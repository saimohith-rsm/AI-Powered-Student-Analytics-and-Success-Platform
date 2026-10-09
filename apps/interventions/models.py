from django.db import models
from django.conf import settings
from apps.students.models import StudentProfile

class InterventionRecord(models.Model):
    class InterventionType(models.TextChoices):
        ACADEMIC_TUTORING = 'ACADEMIC_TUTORING', 'Academic Tutoring & Remedial Classes'
        ATTENDANCE_COUNSELING = 'ATTENDANCE_COUNSELING', 'Attendance Counseling'
        PLACEMENT_PREP = 'PLACEMENT_PREP', 'Placement & Career Mentorship'
        MENTAL_HEALTH = 'MENTAL_HEALTH', 'Wellness & Personal Counseling'
        SKILL_BOOTCAMP = 'SKILL_BOOTCAMP', 'Technical Skill Development'

    class Status(models.TextChoices):
        PROPOSED = 'PROPOSED', 'Proposed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='interventions')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_interventions'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_interventions'
    )
    intervention_type = models.CharField(
        max_length=30,
        choices=InterventionType.choices,
        default=InterventionType.ACADEMIC_TUTORING
    )
    reason = models.TextField(help_text="Detailed justification or AI risk flag driving intervention")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)
    created_at = models.DateTimeField(auto_now_add=True)
    follow_up_date = models.DateField(null=True, blank=True)
    outcome_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Intervention ({self.get_intervention_type_display()}) for {self.student.student_id} [{self.get_status_display()}]"
