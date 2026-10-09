from django.contrib import admin
from .models import LMSActivitySummary

@admin.register(LMSActivitySummary)
class LMSActivitySummaryAdmin(admin.ModelAdmin):
    list_display = ('student', 'login_frequency', 'last_activity_date', 'assignment_completion_pct', 'assignment_timeliness_pct', 'learning_resource_views', 'quiz_participation_pct')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name')
