from django.contrib import admin
from .models import InterventionRecord

@admin.register(InterventionRecord)
class InterventionRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'intervention_type', 'assigned_by', 'assigned_to', 'status', 'created_at', 'follow_up_date')
    list_filter = ('intervention_type', 'status', 'created_at')
    search_fields = ('student__student_id', 'reason', 'outcome_notes')
