from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

from apps.students.models import StudentProfile
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.serializers import StudentSuccessSnapshotSerializer
from apps.analytics.services import StudentAnalyticsEngine
from apps.analytics.queries import latest_snapshots

class BaseStudentAccessMixin:
    """Enforces server-side isolation so students can only view their own analytics records."""
    def check_student_access(self, request, student):
        user = request.user
        if user.is_student_user():
            if not hasattr(user, 'student_profile') or user.student_profile.student_id != student.student_id:
                raise PermissionDenied("Access Denied: You can only access your own academic success records.")
        elif user.is_faculty_user() and not user.is_admin_user():
            # Faculty access is restricted to their assigned department; an unset
            # department is not treated as unrestricted access.
            if not user.department_name or student.department.code != user.department_name:
                raise PermissionDenied("You can only access students in your assigned department.")
        elif not (user.is_admin_user() or user.is_placement_officer()):
            raise PermissionDenied("You do not have permission to access student analytics.")

class StudentSuccessScoreAPIView(BaseStudentAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(StudentProfile, student_id=student_id)
        self.check_student_access(request, student)

        snapshot = latest_snapshots(StudentSuccessSnapshot.objects.filter(student=student)).first()
        if not snapshot:
            snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(student)

        serializer = StudentSuccessSnapshotSerializer(snapshot)
        return Response(serializer.data)

class StudentRiskAssessmentAPIView(BaseStudentAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(StudentProfile, student_id=student_id)
        self.check_student_access(request, student)

        snapshot = latest_snapshots(StudentSuccessSnapshot.objects.filter(student=student)).first()
        if not snapshot:
            snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(student)

        return Response({
            'student_id': student.student_id,
            'student_name': student.full_name,
            'academic_risk_level': snapshot.academic_risk_level,
            'risk_level_display': snapshot.get_academic_risk_level_display(),
            'primary_risk_flags': snapshot.explanation_json.get('risk_flags', []),
            'recommended_interventions': snapshot.explanation_json.get('recommended_interventions', []),
            'segment': snapshot.segment
        })

class PlacementReadinessAPIView(BaseStudentAccessMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(StudentProfile, student_id=student_id)
        self.check_student_access(request, student)

        placement_ass = getattr(student, 'placement_assessments', None)
        latest_placement = student.placement_assessments.first() if placement_ass else None

        return Response({
            'student_id': student.student_id,
            'student_name': student.full_name,
            'overall_placement_readiness': latest_placement.overall_readiness_score if latest_placement else 65.0,
            'aptitude_score': latest_placement.aptitude_score if latest_placement else 65.0,
            'coding_score': latest_placement.coding_score if latest_placement else 65.0,
            'mock_interview_score': latest_placement.mock_interview_score if latest_placement else 65.0,
            'resume_readiness_score': latest_placement.resume_readiness_score if latest_placement else 65.0,
            'communication_score': latest_placement.communication_score if latest_placement else 65.0,
        })

class RecalculateAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not (request.user.is_admin_user() or request.user.is_faculty_user() or request.user.is_placement_officer()):
            raise PermissionDenied("Only faculty and administrators can trigger batch analytics re-computation.")

        students = StudentProfile.objects.filter(enrollment_status='ACTIVE')
        if request.user.is_faculty_user() and not request.user.is_admin_user():
            if not request.user.department_name:
                raise PermissionDenied("Your account has no assigned department.")
            students = students.filter(department__code=request.user.department_name)
        updated_count = 0
        for student in students.iterator():
            StudentAnalyticsEngine.evaluate_and_save_snapshot(student)
            updated_count += 1
        return Response({
            'message': f"Successfully recalculated analytics snapshots for {updated_count} active students.",
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)

class AnalyticsSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_student_user():
            raise PermissionDenied("Students do not have permission to view institutional risk summaries.")

        snapshots = latest_snapshots()
        if request.user.is_faculty_user() and not request.user.is_admin_user():
            if not request.user.department_name:
                raise PermissionDenied("Your account has no assigned department.")
            snapshots = snapshots.filter(student__department__code=request.user.department_name)
        elif not request.user.is_admin_user() and not request.user.is_placement_officer():
            raise PermissionDenied("You do not have permission to view institutional summaries.")
        risk_counts = {
            'LOW': snapshots.filter(academic_risk_level='LOW').count(),
            'MEDIUM': snapshots.filter(academic_risk_level='MEDIUM').count(),
            'HIGH': snapshots.filter(academic_risk_level='HIGH').count(),
            'CRITICAL': snapshots.filter(academic_risk_level='CRITICAL').count(),
        }

        total_students_qs = StudentProfile.objects.filter(enrollment_status='ACTIVE')
        if request.user.is_faculty_user() and not request.user.is_admin_user():
            total_students_qs = total_students_qs.filter(department__code=request.user.department_name)
        total_students = total_students_qs.count()
        avg_score = round(sum([s.overall_success_score for s in snapshots]) / max(1, len(snapshots)), 1) if snapshots.exists() else 0.0

        return Response({
            'total_students': total_students,
            'average_success_score': avg_score,
            'risk_distribution': risk_counts
        })
