from django.contrib import admin
from .models import Subject, SemesterResult, AssessmentResult

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'credits')
    list_filter = ('department', 'credits')
    search_fields = ('code', 'name')

@admin.register(SemesterResult)
class SemesterResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'sgpa', 'cgpa', 'backlog_count', 'passed')
    list_filter = ('semester', 'passed', 'backlog_count')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name')

@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'assessment_name', 'marks_obtained', 'max_marks', 'percentage')
    list_filter = ('subject', 'semester', 'assessment_name')
    search_fields = ('student__student_id', 'subject__code', 'assessment_name')
