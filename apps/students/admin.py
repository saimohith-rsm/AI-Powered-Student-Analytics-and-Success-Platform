from django.contrib import admin
from .models import Department, Program, AcademicYear, Semester, StudentProfile, FacultyAssignment

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'head_of_department')
    search_fields = ('code', 'name', 'head_of_department')

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'degree_level')
    list_filter = ('department', 'degree_level')
    search_fields = ('code', 'name')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('year_label', 'is_current')
    list_filter = ('is_current',)

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('number', 'academic_year', 'is_active')
    list_filter = ('academic_year', 'is_active')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'full_name', 'email', 'department', 'program', 'current_semester', 'enrollment_status')
    list_filter = ('department', 'program', 'current_semester', 'enrollment_status')
    search_fields = ('student_id', 'first_name', 'last_name', 'email')

@admin.register(FacultyAssignment)
class FacultyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('faculty_user', 'department', 'assigned_date')
    list_filter = ('department',)
    search_fields = ('faculty_user__username', 'department__code')
