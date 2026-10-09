from django.contrib import admin
from .models import FeedbackCategory, StudentFeedback, FacultyFeedback

@admin.register(FeedbackCategory)
class FeedbackCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(StudentFeedback)
class StudentFeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'category', 'satisfaction_score', 'is_confidential', 'submitted_date')
    list_filter = ('category', 'satisfaction_score', 'is_confidential')
    search_fields = ('student__student_id', 'comments')

@admin.register(FacultyFeedback)
class FacultyFeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'faculty_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('student__student_id', 'faculty_user__username', 'feedback_text')
