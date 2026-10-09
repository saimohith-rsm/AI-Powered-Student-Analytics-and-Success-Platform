from django.contrib import admin
from .models import AttendanceRecord

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'total_classes', 'classes_attended', 'attendance_percentage', 'last_updated')
    list_filter = ('semester', 'subject')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name')
