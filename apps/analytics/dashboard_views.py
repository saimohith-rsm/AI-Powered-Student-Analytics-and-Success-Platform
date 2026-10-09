import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.students.models import StudentProfile, Department, Program, Semester, AcademicYear
from apps.academics.models import SemesterResult, AssessmentResult, Subject
from apps.attendance.models import AttendanceRecord
from apps.lms.models import LMSActivitySummary
from apps.placements.models import PlacementAssessment, PlacementApplication
from apps.skills.models import StudentSkillAssessment, Skill
from apps.analytics.models import StudentSuccessSnapshot
from apps.analytics.services import StudentAnalyticsEngine
from apps.analytics.queries import latest_snapshots
from apps.interventions.models import InterventionRecord

class BaseScopedQuerysetMixin(LoginRequiredMixin):
    """Base mixin to restrict student querysets according to user roles."""
    def get_scoped_students(self):
        user = self.request.user
        qs = StudentProfile.objects.filter(enrollment_status=StudentProfile.EnrollmentStatus.ACTIVE).select_related('department', 'program', 'user')

        if user.is_admin_user():
            return qs
        elif user.is_faculty_user():
            if user.department_name:
                return qs.filter(department__code=user.department_name)
            return StudentProfile.objects.none()
        elif user.is_placement_officer():
            return qs
        elif user.is_student_user():
            if hasattr(user, 'student_profile'):
                return qs.filter(id=user.student_profile.id)
            return StudentProfile.objects.none()
        return StudentProfile.objects.none()

class OverviewDashboardView(BaseScopedQuerysetMixin, TemplateView):
    template_name = 'dashboards/overview_dashboard.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_student_user():
            if hasattr(user, 'student_profile'):
                return redirect('analytics:student_detail', student_id=user.student_profile.student_id)
            messages.error(request, "Student profile link not found.")
            return redirect('accounts:profile')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        students = self.get_scoped_students()
        
        # Filter Parameters
        dept_code = self.request.GET.get('department')
        sem_num = self.request.GET.get('semester')
        risk_filter = self.request.GET.get('risk_level')

        if dept_code:
            students = students.filter(department__code=dept_code)
        if sem_num:
            students = students.filter(current_semester=sem_num)

        # Base Snapshots for these students
        snapshots = latest_snapshots(StudentSuccessSnapshot.objects.filter(student__in=students))
        if risk_filter:
            snapshots = snapshots.filter(academic_risk_level=risk_filter)

        # Summary Cards
        total_enrolled = students.count()
        avg_success_score = round(snapshots.aggregate(Avg('overall_success_score'))['overall_success_score__avg'] or 0.0, 1)
        students_requiring_review = snapshots.filter(academic_risk_level__in=['HIGH', 'CRITICAL']).values('student').distinct().count()
        
        # Attendance & Placement Aggregates
        att_recs = AttendanceRecord.objects.filter(student__in=students, subject=None)
        att_values = list(att_recs.values_list("classes_attended", "total_classes"))
        valid_attendance = [(attended / total) * 100 for attended, total in att_values if total > 0]
        overall_att_pct = round(sum(valid_attendance) / len(valid_attendance), 1) if valid_attendance else 0.0

        low_placement_count = PlacementAssessment.objects.filter(student__in=students, coding_score__lt=60.0).values("student_id").distinct().count()
        active_interventions_count = InterventionRecord.objects.filter(student__in=students, status__in=['PROPOSED', 'IN_PROGRESS']).count()

        # Risk Distribution Data
        risk_dist = {
            'LOW': snapshots.filter(academic_risk_level='LOW').count(),
            'MEDIUM': snapshots.filter(academic_risk_level='MEDIUM').count(),
            'HIGH': snapshots.filter(academic_risk_level='HIGH').count(),
            'CRITICAL': snapshots.filter(academic_risk_level='CRITICAL').count(),
        }

        # Department Comparisons
        dept_summary = []
        for d in Department.objects.all():
            d_students = students.filter(department=d)
            d_snapshots = snapshots.filter(student__in=d_students)
            d_avg_score = round(d_snapshots.aggregate(Avg('overall_success_score'))['overall_success_score__avg'] or 0.0, 1)
            d_risk_count = d_snapshots.filter(academic_risk_level__in=['HIGH', 'CRITICAL']).count()
            dept_summary.append({
                'code': d.code,
                'name': d.name,
                'student_count': d_students.count(),
                'avg_score': d_avg_score,
                'at_risk_count': d_risk_count
            })

        # Aggregated Insights Engine
        insights = []
        if risk_dist['HIGH'] + risk_dist['CRITICAL'] > 0:
            insights.append({
                'title': 'High Academic & Attendance Risk Detected',
                'badge_class': 'bg-danger',
                'metric': f"{risk_dist['HIGH'] + risk_dist['CRITICAL']} Students",
                'description': 'Students have dropped below mandatory CGPA or 75% attendance thresholds.',
                'action_label': 'Review At-Risk Workspace',
                'action_url': '/risk-monitoring/'
            })

        if low_placement_count > 0:
            insights.append({
                'title': 'Placement Coding Deficiency Flag',
                'badge_class': 'bg-warning text-dark',
                'metric': f"{low_placement_count} Students",
                'description': 'Students possess solid CGPA but score below 60% in coding readiness assessments.',
                'action_label': 'View Placement Readiness',
                'action_url': '/reports/'
            })

        context.update({
            'departments': Department.objects.all(),
            'total_enrolled': total_enrolled,
            'avg_success_score': avg_success_score,
            'students_requiring_review': students_requiring_review,
            'overall_att_pct': overall_att_pct,
            'low_placement_count': low_placement_count,
            'active_interventions_count': active_interventions_count,
            'risk_dist': risk_dist,
            'dept_summary': dept_summary,
            'insights': insights,
            'selected_dept': dept_code or '',
            'selected_sem': sem_num or '',
            'selected_risk': risk_filter or '',
        })
        return context

class StudentDirectoryView(BaseScopedQuerysetMixin, ListView):
    template_name = 'dashboards/student_directory.html'
    model = StudentProfile
    context_object_name = 'students'
    paginate_by = 15

    def get_queryset(self):
        qs = self.get_scoped_students()
        
        # Search query
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(student_id__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )

        # Filters
        dept = self.request.GET.get('department')
        risk = self.request.GET.get('risk_level')
        if dept:
            qs = qs.filter(department__code=dept)
        if risk:
            latest_matching_students = latest_snapshots(
                StudentSuccessSnapshot.objects.filter(student__in=qs)
            ).filter(academic_risk_level=risk).values("student_id")
            qs = qs.filter(pk__in=latest_matching_students)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        context['search_q'] = self.request.GET.get('q', '')
        context['selected_dept'] = self.request.GET.get('department', '')
        context['selected_risk'] = self.request.GET.get('risk_level', '')
        return context

class StudentDetailView(LoginRequiredMixin, DetailView):
    template_name = 'dashboards/student_detail.html'
    model = StudentProfile
    context_object_name = 'student'
    slug_field = 'student_id'
    slug_url_kwarg = 'student_id'

    def get_object(self, queryset=None):
        student = super().get_object(queryset)
        user = self.request.user
        if user.is_student_user():
            if not hasattr(user, 'student_profile') or user.student_profile.student_id != student.student_id:
                raise PermissionDenied("Access Denied: You are restricted to viewing your own student profile.")
        elif user.is_faculty_user() and not user.is_admin_user():
            if not user.department_name or student.department.code != user.department_name:
                raise PermissionDenied("You can only view students in your assigned department.")
        elif not (user.is_admin_user() or user.is_placement_officer()):
            raise PermissionDenied("You do not have permission to view this student profile.")
        return student

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        
        # Calculate/Fetch Latest Snapshot
        snapshot = latest_snapshots(StudentSuccessSnapshot.objects.filter(student=student)).first()
        if not snapshot:
            snapshot = StudentAnalyticsEngine.evaluate_and_save_snapshot(student)

        # Academic Results
        sem_results = SemesterResult.objects.filter(student=student).select_related('semester').order_by('semester__number')
        assessments = AssessmentResult.objects.filter(student=student).select_related('subject', 'semester')
        
        # Attendance Records
        attendance_recs = AttendanceRecord.objects.filter(student=student).select_related('subject', 'semester')
        overall_att = attendance_recs.filter(subject=None).first()

        # LMS Summary
        lms_summary = getattr(student, 'lms_summary', None)

        # Placement Assessments
        placement = student.placement_assessments.first()

        # Skills & Engagement
        skills = StudentSkillAssessment.objects.filter(student=student).select_related('skill')
        engagements = student.engagement_records.select_related('activity')

        # Interventions
        interventions = InterventionRecord.objects.filter(student=student).select_related('assigned_by', 'assigned_to')

        context.update({
            'snapshot': snapshot,
            'sem_results': sem_results,
            'assessments': assessments,
            'attendance_recs': attendance_recs,
            'overall_att': overall_att,
            'lms_summary': lms_summary,
            'placement': placement,
            'skills': skills,
            'engagements': engagements,
            'interventions': interventions,
            'explanation': snapshot.explanation_json if snapshot else {}
        })
        return context

class AtRiskWorkspaceView(BaseScopedQuerysetMixin, ListView):
    template_name = 'dashboards/risk_monitoring.html'
    model = StudentSuccessSnapshot
    context_object_name = 'snapshots'
    paginate_by = 15

    def get_queryset(self):
        scoped_students = self.get_scoped_students()
        qs = latest_snapshots(StudentSuccessSnapshot.objects.filter(
            student__in=scoped_students,
        )).filter(academic_risk_level__in=['HIGH', 'CRITICAL']).select_related(
            'student', 'student__department', 'student__program'
        ).order_by('-snapshot_date', 'overall_success_score')

        dept = self.request.GET.get('department')
        if dept:
            qs = qs.filter(student__department__code=dept)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        context['critical_count'] = self.get_queryset().filter(academic_risk_level='CRITICAL').count()
        context['high_count'] = self.get_queryset().filter(academic_risk_level='HIGH').count()
        return context

class SegmentationView(BaseScopedQuerysetMixin, TemplateView):
    template_name = 'dashboards/segmentation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scoped_students = self.get_scoped_students()
        snapshots = latest_snapshots(StudentSuccessSnapshot.objects.filter(student__in=scoped_students))

        segments = [
            {
                'name': 'High Performing',
                'badge': 'bg-success',
                'definition': 'Top academic rank (CGPA >= 8.5, Attendance >= 85%, High Success Score).',
                'count': snapshots.filter(segment='High Performing').count(),
                'students': snapshots.filter(segment='High Performing')[:5]
            },
            {
                'name': 'Academic Risk',
                'badge': 'bg-danger',
                'definition': 'Low CGPA (< 6.5) or active backlogs requiring academic tutoring.',
                'count': snapshots.filter(segment='Academic Risk').count(),
                'students': snapshots.filter(segment='Academic Risk')[:5]
            },
            {
                'name': 'Attendance Risk',
                'badge': 'bg-warning text-dark',
                'definition': 'Attendance below institutional requirement (< 75%).',
                'count': snapshots.filter(segment='Attendance Risk').count(),
                'students': snapshots.filter(segment='Attendance Risk')[:5]
            },
            {
                'name': 'Placement Support Needed',
                'badge': 'bg-info text-dark',
                'definition': 'Good academic CGPA but scoring below 60% in coding/aptitude assessments.',
                'count': snapshots.filter(segment='Placement Support Needed').count(),
                'students': snapshots.filter(segment='Placement Support Needed')[:5]
            },
            {
                'name': 'LMS Disengaged',
                'badge': 'bg-secondary',
                'definition': 'Low assignment completion (< 60%) or inactive LMS logins.',
                'count': snapshots.filter(segment='LMS Disengaged').count(),
                'students': snapshots.filter(segment='LMS Disengaged')[:5]
            }
        ]

        context['segments'] = segments
        return context

class InterventionManagementView(BaseScopedQuerysetMixin, ListView):
    template_name = 'dashboards/intervention_management.html'
    model = InterventionRecord
    context_object_name = 'interventions'
    paginate_by = 15

    def get_queryset(self):
        scoped_students = self.get_scoped_students()
        qs = InterventionRecord.objects.filter(student__in=scoped_students).select_related('student', 'assigned_by', 'assigned_to')

        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = InterventionRecord.Status.choices
        context['selected_status'] = self.request.GET.get('status', '')
        return context

class CreateOrUpdateInterventionView(LoginRequiredMixin, View):
    """Create or update an intervention record with closed-loop outcome notes."""
    def post(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_admin_user() or user.is_faculty_user()):
            raise PermissionDenied("Only faculty and administrators can manage interventions.")

        intervention_id = request.POST.get('intervention_id')
        student_id = request.POST.get('student_id')
        intervention_type = request.POST.get('intervention_type')
        reason = request.POST.get('reason')
        status_val = request.POST.get('status', InterventionRecord.Status.PROPOSED)
        outcome_notes = request.POST.get('outcome_notes', '')

        if intervention_id:
            intervention = get_object_or_404(InterventionRecord, id=intervention_id)
            if user.is_faculty_user() and not user.is_admin_user():
                if not user.department_name or intervention.student.department.code != user.department_name:
                    raise PermissionDenied("You can only manage interventions for your assigned department.")
            allowed_statuses = {choice[0] for choice in InterventionRecord.Status.choices}
            if status_val not in allowed_statuses:
                messages.error(request, "Invalid intervention status.")
                return redirect('analytics:intervention_management')
            intervention.status = status_val
            if outcome_notes:
                intervention.outcome_notes = outcome_notes
            intervention.save()
            messages.success(request, f"Intervention for {intervention.student.student_id} updated successfully.")
        else:
            student = get_object_or_404(StudentProfile, student_id=student_id)
            if user.is_faculty_user() and not user.is_admin_user():
                if not user.department_name or student.department.code != user.department_name:
                    raise PermissionDenied("You can only manage interventions for your assigned department.")
            allowed_types = {choice[0] for choice in InterventionRecord.InterventionType.choices}
            allowed_statuses = {choice[0] for choice in InterventionRecord.Status.choices}
            if intervention_type not in allowed_types or status_val not in allowed_statuses or not reason:
                messages.error(request, "Please provide a valid intervention type, status, and reason.")
                return redirect('analytics:intervention_management')
            InterventionRecord.objects.create(
                student=student,
                assigned_by=user,
                assigned_to=user,
                intervention_type=intervention_type,
                reason=reason,
                status=status_val,
                outcome_notes=outcome_notes
            )
            messages.success(request, f"New intervention logged for student {student_id}.")

        return redirect('analytics:intervention_management')

class ReportsExportView(BaseScopedQuerysetMixin, TemplateView):
    template_name = 'dashboards/reports.html'

class ExportReportCSVView(BaseScopedQuerysetMixin, View):
    """Generates role-scoped CSV exports for institution reporting."""

    @staticmethod
    def _safe_csv_row(writer, values):
        # Prefix formula-like cells to prevent spreadsheet formula injection.
        safe_values = []
        for value in values:
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                value = "'" + value
            safe_values.append(value)
        writer.writerow(safe_values)

    def get(self, request, report_type):
        user = request.user
        if user.is_student_user():
            raise PermissionDenied("Students are not permitted to export bulk institution reports.")

        if report_type not in {"risk", "placement", "interventions"}:
            from django.http import Http404
            raise Http404("Unknown report type.")

        scoped_students = self.get_scoped_students()

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="smart_campus_{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)

        if report_type == 'risk':
            writer.writerow(['Student ID', 'Full Name', 'Department', 'Semester', 'Success Score', 'Risk Level', 'Primary Risk Flags'])
            snapshots = latest_snapshots(StudentSuccessSnapshot.objects.filter(student__in=scoped_students)).filter(academic_risk_level__in=['HIGH', 'CRITICAL'])
            for s in snapshots:
                flags = "; ".join(s.explanation_json.get('risk_flags', []))
                self._safe_csv_row(writer, [s.student.student_id, s.student.full_name, s.student.department.code, s.student.current_semester, s.overall_success_score, s.academic_risk_level, flags])

        elif report_type == 'placement':
            writer.writerow(['Student ID', 'Full Name', 'Department', 'Readiness Score', 'Aptitude Score', 'Coding Score', 'Mock Interview Score'])
            assessments = PlacementAssessment.objects.filter(student__in=scoped_students)
            for p in assessments:
                self._safe_csv_row(writer, [p.student.student_id, p.student.full_name, p.student.department.code, p.overall_readiness_score, p.aptitude_score, p.coding_score, p.mock_interview_score])

        elif report_type == 'interventions':
            writer.writerow(['Student ID', 'Type', 'Reason', 'Assigned By', 'Status', 'Created Date', 'Outcome Notes'])
            records = InterventionRecord.objects.filter(student__in=scoped_students)
            for r in records:
                self._safe_csv_row(writer, [r.student.student_id, r.get_intervention_type_display(), r.reason, r.assigned_by.username if r.assigned_by else '', r.get_status_display(), r.created_at.strftime("%Y-%m-%d"), r.outcome_notes or ''])

        else:
            from django.http import Http404
            raise Http404("Unknown report type.")

        return response


class CSVRiskCheckerAndImportView(BaseScopedQuerysetMixin, View):
    """Interactive workspace for uploading CSV/Excel datasets to check student risk or import."""
    template_name = 'dashboards/csv_risk_checker.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_student_user():
            raise PermissionDenied("Students are not permitted to access batch risk verification.")

        from apps.analytics.risk_checker import CSVRiskCheckerService
        context = {
            'column_specs': CSVRiskCheckerService.COLUMN_SPECS,
            'canonical_header_csv': CSVRiskCheckerService.get_canonical_header_csv(),
            'analysis_completed': False,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_student_user():
            raise PermissionDenied("Students are not permitted to access batch risk verification.")

        from apps.analytics.risk_checker import CSVRiskCheckerService
        from apps.students.services import DataImportService
        from django.conf import settings
        from django.core.files.storage import FileSystemStorage
        from pathlib import Path
        import os
        import logging

        logger = logging.getLogger(__name__)

        dataset_file = request.FILES.get("dataset_file")
        action = request.POST.get("action", "analyze")  # "analyze" or "import_and_analyze"

        if not dataset_file:
            messages.error(request, "Please select a CSV or Excel file to check.")
            return redirect("analytics:csv_risk_checker")

        if dataset_file.size > 5 * 1024 * 1024:
            messages.error(request, "The upload exceeds the 5 MB limit.")
            return redirect("analytics:csv_risk_checker")

        original_name = Path(dataset_file.name).name
        ext = Path(original_name).suffix.lower()
        if ext not in {".csv", ".xlsx", ".xls"}:
            messages.error(request, "Unsupported file format. Please upload a .csv, .xlsx, or .xls file.")
            return redirect("analytics:csv_risk_checker")

        # Save to temp directory for processing
        import_dir = Path(settings.MEDIA_ROOT) / "temp_risk_checks"
        import_dir.mkdir(parents=True, exist_ok=True)
        storage = FileSystemStorage(location=str(import_dir))
        filename = storage.save(original_name, dataset_file)
        file_path = storage.path(filename)

        try:
            # 1. Run in-memory Risk Analysis
            with open(file_path, "rb") as f:
                analysis_results = CSVRiskCheckerService.analyze_file(f, filename=original_name)

            imported_count = 0
            import_errors = []
            did_import = False

            # 2. If user requested to commit records to the database
            if action == "import_and_analyze":
                if not (user.is_admin_user() or user.is_faculty_user()):
                    messages.warning(request, "Only Administrators and Faculty can commit records to the database. File was evaluated in preview mode.")
                else:
                    import_res = DataImportService.import_from_file(file_path, evaluate_analytics=True)
                    imported_count = import_res.get("imported_count", 0)
                    import_errors = import_res.get("errors", [])
                    did_import = True
                    if imported_count > 0:
                        messages.success(
                            request,
                            f"Risk check complete! Successfully imported and generated live analytics snapshots for {imported_count} students."
                        )
                    if import_errors:
                        messages.warning(request, f"Import encountered {len(import_errors)} row warning(s).")
            else:
                messages.info(request, f"Analyzed {analysis_results['valid_rows']} student record(s) from '{original_name}' (Preview Mode - Database not modified).")

            context = {
                'column_specs': CSVRiskCheckerService.COLUMN_SPECS,
                'canonical_header_csv': CSVRiskCheckerService.get_canonical_header_csv(),
                'analysis_completed': True,
                'results': analysis_results,
                'did_import': did_import,
                'imported_count': imported_count,
                'import_errors': import_errors,
                'filename': original_name,
            }
            return render(request, self.template_name, context)

        except ValueError as val_err:
            messages.error(request, str(val_err))
            return redirect("analytics:csv_risk_checker")
        except Exception as exc:
            logger.exception("Error checking CSV risk")
            messages.error(request, f"Error processing file: {exc}")
            return redirect("analytics:csv_risk_checker")
        finally:
            try:
                os.remove(file_path)
            except (OSError, FileNotFoundError):
                pass


class DownloadSampleCSVTemplateView(LoginRequiredMixin, View):
    """Direct download endpoint for the sample CSV student dataset template."""
    def get(self, request, *args, **kwargs):
        from django.conf import settings
        from django.http import FileResponse, HttpResponse
        import os

        template_path = os.path.join(settings.BASE_DIR, "static", "data", "sample_student_import_template.csv")
        if not os.path.exists(template_path):
            template_path = os.path.join(settings.BASE_DIR, "sample_student_import_template.csv")

        if os.path.exists(template_path):
            response = FileResponse(open(template_path, 'rb'), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sample_student_import_template.csv"'
            return response
        else:
            from apps.analytics.risk_checker import CSVRiskCheckerService
            response = HttpResponse(CSVRiskCheckerService.get_canonical_header_csv() + "\n", content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sample_student_import_template.csv"'
            return response


class SendStudentRiskAlertView(BaseScopedQuerysetMixin, View):
    """Dispatches a personalized email risk advisory to an at-risk student."""
    def post(self, request, student_id):
        user = request.user
        if user.is_student_user():
            raise PermissionDenied("Students cannot dispatch risk alerts.")

        scoped_students = self.get_scoped_students()
        student = get_object_or_404(scoped_students, student_id=student_id)

        custom_note = request.POST.get("custom_note", "").strip() or None

        from apps.analytics.alert_service import StudentRiskAlertService
        result = StudentRiskAlertService.send_individual_alert(
            student=student,
            sender_user=user,
            custom_note=custom_note,
            create_intervention=True
        )

        if result.get("success"):
            messages.success(
                request,
                f"Risk alert email successfully dispatched to {student.full_name} ({result.get('email')}). Counseling intervention recorded."
            )
        else:
            messages.error(
                request,
                f"Failed to send email alert to {student.full_name}: {result.get('error', 'Unknown error')}"
            )

        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "analytics:risk_monitoring"
        return redirect(next_url)


class SendBatchRiskAlertsView(BaseScopedQuerysetMixin, View):
    """Sends email alerts in bulk to all currently scoped at-risk (HIGH & CRITICAL) students."""
    def post(self, request):
        user = request.user
        if user.is_student_user():
            raise PermissionDenied("Students cannot dispatch batch risk alerts.")

        scoped_students = self.get_scoped_students()
        at_risk_students_qs = scoped_students.filter(
            pk__in=latest_snapshots(
                StudentSuccessSnapshot.objects.filter(student__in=scoped_students)
            ).filter(academic_risk_level__in=['HIGH', 'CRITICAL']).values('student_id')
        )

        custom_note = request.POST.get("custom_note", "").strip() or None

        from apps.analytics.alert_service import StudentRiskAlertService
        result = StudentRiskAlertService.send_batch_alerts(
            students=list(at_risk_students_qs),
            sender_user=user,
            custom_note=custom_note,
        )

        sent = result.get("sent", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)

        if total == 0:
            messages.info(request, "No high or critical risk students found to alert.")
        elif failed == 0:
            messages.success(request, f"Successfully dispatched advisory emails to all {sent} at-risk students.")
        else:
            messages.warning(request, f"Dispatched {sent} alert emails, but {failed} could not be delivered.")

        return redirect("analytics:risk_monitoring")


