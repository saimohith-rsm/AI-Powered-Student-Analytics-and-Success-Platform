from django.contrib import admin
from .models import PlacementAssessment, PlacementApplication

@admin.register(PlacementAssessment)
class PlacementAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment_date', 'aptitude_score', 'coding_score', 'mock_interview_score', 'overall_readiness_score')
    list_filter = ('assessment_date',)
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name')

@admin.register(PlacementApplication)
class PlacementApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'company_name', 'role_offered', 'status', 'package_lpa', 'applied_date')
    list_filter = ('status', 'company_name')
    search_fields = ('student__student_id', 'company_name', 'role_offered')
