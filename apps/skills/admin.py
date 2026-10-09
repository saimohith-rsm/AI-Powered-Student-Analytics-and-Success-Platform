from django.contrib import admin
from .models import Skill, StudentSkillAssessment

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(StudentSkillAssessment)
class StudentSkillAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'skill', 'proficiency_score', 'assessed_date')
    list_filter = ('skill__category', 'skill')
    search_fields = ('student__student_id', 'skill__name')
