from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from apps.students.models import StudentProfile, Department, Semester

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="Subject Code, e.g. CS201")
    name = models.CharField(max_length=150, help_text="Subject Name, e.g. Data Structures")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    credits = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(10)])

    def __str__(self):
        return f"{self.code} - {self.name} ({self.credits} credits)"

class SemesterResult(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='semester_results')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='student_results')
    sgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0.00), MaxValueValidator(10.00)],
        help_text="Semester GPA (0.00 - 10.00)"
    )
    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0.00), MaxValueValidator(10.00)],
        help_text="Cumulative GPA (0.00 - 10.00)"
    )
    credits_completed = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    backlog_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    passed = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'semester')
        ordering = ['student', 'semester']

    def clean(self):
        super().clean()
        if self.sgpa < 0 or self.sgpa > 10:
            raise ValidationError({'sgpa': 'SGPA must be between 0.00 and 10.00.'})
        if self.cgpa < 0 or self.cgpa > 10:
            raise ValidationError({'cgpa': 'CGPA must be between 0.00 and 10.00.'})

    def __str__(self):
        return f"{self.student.student_id} - {self.semester}: CGPA {self.cgpa}"

class AssessmentResult(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assessment_results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='subject_assessments')
    assessment_name = models.CharField(max_length=100, help_text="e.g. Midterm, Quiz 1, Final Exam")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00)])
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, validators=[MinValueValidator(1.00)])

    class Meta:
        ordering = ['student', 'subject', 'assessment_name']

    def clean(self):
        super().clean()
        if self.marks_obtained > self.max_marks:
            raise ValidationError({'marks_obtained': f'Marks obtained ({self.marks_obtained}) cannot exceed max marks ({self.max_marks}).'})

    @property
    def percentage(self):
        if self.max_marks and self.max_marks > 0:
            return round((float(self.marks_obtained) / float(self.max_marks)) * 100, 2)
        return 0.0

    def __str__(self):
        return f"{self.student.student_id} - {self.subject.code} ({self.assessment_name}): {self.marks_obtained}/{self.max_marks}"
