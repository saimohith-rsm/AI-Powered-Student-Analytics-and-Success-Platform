from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from apps.students.models import StudentProfile, Semester
from apps.academics.models import Subject

class AttendanceRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='attendance_records')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='attendance_records')
    total_classes = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    classes_attended = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student', 'semester', 'subject']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'semester', 'subject'],
                condition=models.Q(subject__isnull=False),
                name='unique_student_semester_subject_attendance',
            ),
            models.UniqueConstraint(
                fields=['student', 'semester'],
                condition=models.Q(subject__isnull=True),
                name='unique_student_semester_overall_attendance',
            ),
        ]

    def clean(self):
        super().clean()
        if self.classes_attended > self.total_classes:
            raise ValidationError({
                'classes_attended': f'Classes attended ({self.classes_attended}) cannot exceed total classes conducted ({self.total_classes}).'
            })

    @property
    def attendance_percentage(self):
        if self.total_classes and self.total_classes > 0:
            return round((self.classes_attended / self.total_classes) * 100.0, 2)
        return 0.0

    def __str__(self):
        subject_label = self.subject.code if self.subject else 'Overall'
        return f"{self.student.student_id} - {subject_label}: {self.attendance_percentage}% ({self.classes_attended}/{self.total_classes})"
