from django.urls import path
from .views import (
    UserLoginView, UserLogoutView, UserRegisterView, DashboardRedirectView,
    AdminDashboardStubView, FacultyDashboardStubView,
    PlacementDashboardStubView, StudentDashboardStubView,
    UserProfileView
)

app_name = 'accounts'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardRedirectView.as_view(), name='dashboard_redirect'),
    path('dashboard/admin/', AdminDashboardStubView.as_view(), name='admin_dashboard_stub'),
    path('dashboard/faculty/', FacultyDashboardStubView.as_view(), name='faculty_dashboard_stub'),
    path('dashboard/placement/', PlacementDashboardStubView.as_view(), name='placement_dashboard_stub'),
    path('dashboard/student/', StudentDashboardStubView.as_view(), name='student_dashboard_stub'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]
