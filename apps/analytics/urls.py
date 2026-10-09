from django.urls import path
from apps.analytics.views import (
    StudentSuccessScoreAPIView,
    StudentRiskAssessmentAPIView,
    PlacementReadinessAPIView,
    RecalculateAnalyticsAPIView,
    AnalyticsSummaryAPIView
)
from apps.analytics.dashboard_views import (
    OverviewDashboardView,
    StudentDirectoryView,
    StudentDetailView,
    AtRiskWorkspaceView,
    SegmentationView,
    InterventionManagementView,
    CreateOrUpdateInterventionView,
    ReportsExportView,
    ExportReportCSVView,
    CSVRiskCheckerAndImportView,
    DownloadSampleCSVTemplateView,
    SendStudentRiskAlertView,
    SendBatchRiskAlertsView
)

app_name = 'analytics'

urlpatterns = [
    # Dashboard Pages
    path('dashboard/', OverviewDashboardView.as_view(), name='overview_dashboard'),
    path('students/', StudentDirectoryView.as_view(), name='student_directory'),
    path('students/<str:student_id>/', StudentDetailView.as_view(), name='student_detail'),
    path('risk-monitoring/', AtRiskWorkspaceView.as_view(), name='risk_monitoring'),
    path('risk-monitoring/alert/<str:student_id>/', SendStudentRiskAlertView.as_view(), name='send_risk_alert'),
    path('risk-monitoring/batch-alert/', SendBatchRiskAlertsView.as_view(), name='send_batch_risk_alerts'),
    path('risk-checker/', CSVRiskCheckerAndImportView.as_view(), name='csv_risk_checker'),
    path('risk-checker/template/', DownloadSampleCSVTemplateView.as_view(), name='download_sample_template'),
    path('segments/', SegmentationView.as_view(), name='segmentation'),
    path('interventions/', InterventionManagementView.as_view(), name='intervention_management'),
    path('interventions/action/', CreateOrUpdateInterventionView.as_view(), name='intervention_action'),
    path('reports/', ReportsExportView.as_view(), name='reports'),
    path('reports/export/<str:report_type>/', ExportReportCSVView.as_view(), name='export_report'),

    # REST APIs (Part 2)
    path('api/analytics/success-score/<str:student_id>/', StudentSuccessScoreAPIView.as_view(), name='api_success_score'),
    path('api/analytics/risk-assessment/<str:student_id>/', StudentRiskAssessmentAPIView.as_view(), name='api_risk_assessment'),
    path('api/analytics/placement-readiness/<str:student_id>/', PlacementReadinessAPIView.as_view(), name='api_placement_readiness'),
    path('api/analytics/recalculate/', RecalculateAnalyticsAPIView.as_view(), name='api_recalculate'),
    path('api/analytics/summary/', AnalyticsSummaryAPIView.as_view(), name='api_summary'),
]
