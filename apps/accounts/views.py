from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import validate_email

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from apps.accounts.models import User
from apps.students.models import StudentProfile, Department, Program
from apps.analytics.services import StudentAnalyticsEngine

class LandingPageView(TemplateView):
    template_name = 'landing.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard_redirect')
        return super().get(request, *args, **kwargs)

@method_decorator(never_cache, name='dispatch')
class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('accounts:dashboard_redirect')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

@method_decorator(never_cache, name='dispatch')
class UserRegisterView(View):
    template_name = 'accounts/register.html'

    def get_departments(self):
        try:
            return list(Department.objects.all())
        except Exception:
            try:
                from config.db_init import ensure_database_initialized
                ensure_database_initialized()
                return list(Department.objects.all())
            except Exception:
                return []

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard_redirect')
        if not settings.ALLOW_PUBLIC_STUDENT_REGISTRATION:
            raise PermissionDenied("Public registration is disabled. Contact your campus administrator.")
        departments = self.get_departments()
        return render(request, self.template_name, {'departments': departments})

    def post(self, request, *args, **kwargs):
        if not settings.ALLOW_PUBLIC_STUDENT_REGISTRATION:
            raise PermissionDenied("Public registration is disabled. Contact your campus administrator.")
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        student_id_input = request.POST.get('student_id', '').strip()
        dept_id = request.POST.get('department')

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, self.template_name, {'departments': self.get_departments()})
        if len(username) > 150 or len(first_name) > 150 or len(last_name) > 150:
            messages.error(request, "Username and name fields must be within their supported length limits.")
            return render(request, self.template_name, {'departments': self.get_departments()})
        if email:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
                return render(request, self.template_name, {'departments': self.get_departments()})
        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, self.template_name, {'departments': self.get_departments()})

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' is already taken. Please choose another username.")
            return render(request, self.template_name, {'departments': self.get_departments()})

        profile_email = email or f"{username}@campus.edu"
        if User.objects.filter(email__iexact=profile_email).exists() or StudentProfile.objects.filter(email__iexact=profile_email).exists():
            messages.error(request, f"Email '{profile_email}' is already registered.")
            return render(request, self.template_name, {'departments': self.get_departments()})

        # Security: Public self-registration is strictly restricted to STUDENT role.
        # Faculty, Placement, and Admin accounts must be created by an existing Administrator.
        role = User.Role.STUDENT

        user = User.objects.create_user(
            username=username,
            email=profile_email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        student_id = student_id_input.upper() if student_id_input else f"STU{user.id:04d}"
        if StudentProfile.objects.filter(student_id__iexact=student_id).exists():
            user.delete()
            messages.error(request, "That student ID is already registered. Please use your assigned student ID.")
            return render(request, self.template_name, {'departments': self.get_departments()})
        dept = Department.objects.filter(id=dept_id).first() if dept_id else Department.objects.first()
        if not dept:
            dept = Department.objects.create(code='CSE', name='Computer Science & Engineering')
        prog = dept.programs.first() if dept else None
        if not prog and dept:
            prog = Program.objects.create(code=f'BTECH-{dept.code}', name=f'B.Tech in {dept.name}', department=dept)
        
        student_profile = StudentProfile.objects.create(
            user=user,
            student_id=student_id,
            first_name=first_name or username,
            last_name=last_name or 'Student',
            email=profile_email,
            department=dept,
            program=prog,
            admission_year=timezone.localdate().year,
            current_semester=1
        )
        StudentAnalyticsEngine.evaluate_and_save_snapshot(student_profile)

        login(request, user)
        messages.success(request, f"Account successfully created! Welcome to Smart Campus Analytics, {user.username}.")
        return redirect('accounts:dashboard_redirect')

class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_student_user():
            if hasattr(user, 'student_profile'):
                messages.info(request, f"Welcome Student, {user.first_name or user.username}!")
                return redirect('analytics:student_detail', student_id=user.student_profile.student_id)
            return redirect('accounts:profile')
        else:
            messages.info(request, f"Welcome {user.get_role_display()}, {user.username}!")
            return redirect('analytics:overview_dashboard')

class AdminDashboardStubView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/admin_dashboard.html'

class FacultyDashboardStubView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/faculty_dashboard.html'

class PlacementDashboardStubView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/placement_dashboard.html'

class StudentDashboardStubView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/student_dashboard.html'

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)

def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)
