from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import StudentProfile

class Skill(models.Model):
    class SkillCategory(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical Skill'
        SOFT_SKILL = 'SOFT', 'Soft Skill'

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=SkillCategory.choices, default=SkillCategory.TECHNICAL)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class StudentSkillAssessment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='skill_assessments')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='student_assessments')
    proficiency_score = models.FloatField(
        default=50.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Skill proficiency score (0-100)"
    )
    assessed_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'skill')

    def __str__(self):
        return f"{self.student.student_id} - {self.skill.name}: {self.proficiency_score}/100"
