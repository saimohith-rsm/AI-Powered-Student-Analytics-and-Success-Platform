from django.contrib import admin
from .models import StudentSuccessSnapshot

@admin.register(StudentSuccessSnapshot)
class StudentSuccessSnapshotAdmin(admin.ModelAdmin):
    list_display = ('student', 'snapshot_date', 'overall_success_score', 'academic_risk_level', 'placement_readiness_score', 'segment')
    list_filter = ('academic_risk_level', 'segment', 'snapshot_date')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name', 'segment')
