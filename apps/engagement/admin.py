from django.contrib import admin
from .models import ActivityCategory, EngagementActivity, StudentEngagement

@admin.register(ActivityCategory)
class ActivityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EngagementActivity)
class EngagementActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'event_date', 'organizer')
    list_filter = ('category', 'event_date')
    search_fields = ('title', 'organizer')

@admin.register(StudentEngagement)
class StudentEngagementAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'role', 'engagement_score')
    list_filter = ('activity__category', 'role')
    search_fields = ('student__student_id', 'activity__title')
