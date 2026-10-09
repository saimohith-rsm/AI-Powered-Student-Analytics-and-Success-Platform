import numpy as np
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.students.models import StudentProfile
from apps.academics.models import SemesterResult, AssessmentResult
from apps.attendance.models import AttendanceRecord
from apps.lms.models import LMSActivitySummary
from apps.placements.models import PlacementAssessment
from apps.skills.models import StudentSkillAssessment
from apps.feedback.models import StudentFeedback
from apps.engagement.models import StudentEngagement
from apps.analytics.models import StudentSuccessSnapshot
from apps.interventions.models import InterventionRecord

class StudentAnalyticsEngine:
    """Core AI Analytics & Student Success Engine.
    
    Computes explainable student success scores, predicts academic and attendance risk,
    determines placement readiness, segments students, and triggers automated interventions.
    """

    @classmethod
    def calculate_student_success_score(cls, student: StudentProfile):
        """Calculates explainable student success score (0-100) and detailed factor breakdown."""
        
        # Track source coverage so defaults are visible to staff and not mistaken for observations.
        data_availability = {
            "academic": SemesterResult.objects.filter(student=student).exists(),
            "attendance": AttendanceRecord.objects.filter(student=student).exists(),
            "lms": hasattr(student, "lms_summary"),
            "placement": PlacementAssessment.objects.filter(student=student).exists(),
            "skills": StudentSkillAssessment.objects.filter(student=student).exists(),
            "engagement": StudentEngagement.objects.filter(student=student).exists(),
            "feedback": StudentFeedback.objects.filter(student=student).exists(),
        }

        # 1. Academic Sub-Score (Weight: 30%)
        latest_sem_result = SemesterResult.objects.filter(student=student).order_by('-semester__number').first()
        cgpa = float(latest_sem_result.cgpa) if latest_sem_result else 7.0
        backlogs = latest_sem_result.backlog_count if latest_sem_result else 0
        
        # Base academic score = CGPA * 10 - (Backlogs * 10)
        academic_score = max(0.0, min(100.0, (cgpa * 10.0) - (backlogs * 10.0)))
        
        # 2. Attendance Sub-Score (Weight: 25%)
        attendance_rec = AttendanceRecord.objects.filter(student=student, subject=None).first()
        if not attendance_rec:
            # Fallback to subject records average if overall record is missing
            sub_records = AttendanceRecord.objects.filter(student=student)
            if sub_records.exists():
                attendance_pct = float(np.mean([r.attendance_percentage for r in sub_records]))
            else:
                attendance_pct = 80.0
        else:
            attendance_pct = attendance_rec.attendance_percentage
            
        attendance_score = attendance_pct
        if attendance_pct < 60.0:
            attendance_score = min(attendance_score, 40.0) # Severe penalty for compliance breach

        # 3. LMS Engagement Sub-Score (Weight: 15%)
        lms_summary = getattr(student, 'lms_summary', None)
        if lms_summary:
            comp_pct = lms_summary.assignment_completion_pct
            time_pct = lms_summary.assignment_timeliness_pct
            quiz_pct = lms_summary.quiz_participation_pct
            login_freq = min(100.0, (lms_summary.login_frequency / 20.0) * 100.0)
            
            lms_score = (0.40 * comp_pct) + (0.30 * time_pct) + (0.20 * quiz_pct) + (0.10 * login_freq)
            
            # Inactivity penalty
            if lms_summary.last_activity_date:
                days_inactive = (timezone.now() - lms_summary.last_activity_date).days
                if days_inactive > 7:
                    lms_score = max(0.0, lms_score - (days_inactive * 2))
        else:
            lms_score = 70.0 # Default benchmark if missing

        # 4. Placement Readiness Sub-Score (Weight: 15%)
        placement_ass = PlacementAssessment.objects.filter(student=student).first()
        if placement_ass:
            placement_score = placement_ass.overall_readiness_score
            coding_score = placement_ass.coding_score
            aptitude_score = placement_ass.aptitude_score
        else:
            placement_score = 65.0
            coding_score = 65.0
            aptitude_score = 65.0

        # 5. Skills & Extracurricular Sub-Score (Weight: 15%)
        skill_records = StudentSkillAssessment.objects.filter(student=student)
        if skill_records.exists():
            avg_skill = float(np.mean([s.proficiency_score for s in skill_records]))
        else:
            avg_skill = 70.0
            
        engagement_records = StudentEngagement.objects.filter(student=student)
        if engagement_records.exists():
            avg_engagement = float(np.mean([e.engagement_score for e in engagement_records]))
        else:
            avg_engagement = 50.0
            
        skills_eng_score = (0.60 * avg_skill) + (0.40 * avg_engagement)

        # Placement-specific risk is kept separate from academic risk.
        if not PlacementAssessment.objects.filter(student=student).exists():
            placement_risk_level = "UNKNOWN"
        elif placement_score < 35.0:
            placement_risk_level = "CRITICAL"
        elif placement_score < 50.0:
            placement_risk_level = "HIGH"
        elif placement_score < 65.0:
            placement_risk_level = "MEDIUM"
        else:
            placement_risk_level = "LOW"

        # Overall Weighted Composite Score
        overall_success_score = round(
            (0.30 * academic_score) +
            (0.25 * attendance_score) +
            (0.15 * lms_score) +
            (0.15 * placement_score) +
            (0.15 * skills_eng_score),
            1
        )

        # 6. Risk Level Determination
        risk_flags = []
        positive_factors = []
        recommended_interventions = []

        if cgpa >= 8.5:
            positive_factors.append(f"Outstanding CGPA: {cgpa:.2f}")
        elif cgpa < 6.0:
            risk_flags.append(f"Low CGPA Warning: {cgpa:.2f}")

        if backlogs > 0:
            risk_flags.append(f"Active Backlogs: {backlogs}")

        if attendance_pct >= 90:
            positive_factors.append(f"Excellent Attendance: {attendance_pct:.1f}%")
        elif attendance_pct < 75:
            risk_flags.append(f"Mandatory Attendance Deficit: {attendance_pct:.1f}% (Below 75% threshold)")

        if lms_summary and lms_summary.assignment_completion_pct < 65:
            risk_flags.append(f"Low LMS Assignment Completion: {lms_summary.assignment_completion_pct:.1f}%")

        if coding_score < 55:
            risk_flags.append(f"Weak Coding Proficiency: {coding_score:.1f}%")

        # Determine Risk Level
        if cgpa < 5.0 or attendance_pct < 60.0 or backlogs >= 3 or overall_success_score < 45.0:
            risk_level = StudentSuccessSnapshot.RiskLevel.CRITICAL
        elif cgpa < 6.5 or attendance_pct < 75.0 or backlogs >= 1 or overall_success_score < 60.0:
            risk_level = StudentSuccessSnapshot.RiskLevel.HIGH
        elif cgpa < 7.5 or attendance_pct < 85.0 or overall_success_score < 75.0:
            risk_level = StudentSuccessSnapshot.RiskLevel.MEDIUM
        else:
            risk_level = StudentSuccessSnapshot.RiskLevel.LOW

        # Recommended Interventions
        if cgpa < 6.5 or backlogs > 0:
            recommended_interventions.append(InterventionRecord.InterventionType.ACADEMIC_TUTORING)
        if attendance_pct < 75.0:
            recommended_interventions.append(InterventionRecord.InterventionType.ATTENDANCE_COUNSELING)
        if coding_score < 60.0 or aptitude_score < 60.0:
            recommended_interventions.append(InterventionRecord.InterventionType.PLACEMENT_PREP)

        # 7. Student Segmentation
        if overall_success_score >= 85.0 and cgpa >= 8.5 and attendance_pct >= 85.0:
            segment = "High Performing"
        elif cgpa < 6.5 or backlogs > 0:
            segment = "Academic Risk"
        elif attendance_pct < 75.0:
            segment = "Attendance Risk"
        elif cgpa >= 7.0 and coding_score < 60.0:
            segment = "Placement Support Needed"
        elif lms_summary and lms_summary.assignment_completion_pct < 60.0:
            segment = "LMS Disengaged"
        else:
            segment = "On Track / General Student"

        # Construct Explainable JSON
        explanation_json = {
            'cgpa': cgpa,
            'backlog_count': backlogs,
            'attendance_percentage': attendance_pct,
            'lms_completion_percentage': lms_summary.assignment_completion_pct if lms_summary else 70.0,
            'coding_score': coding_score,
            'data_availability': data_availability,
            'sub_scores': {
                'academic_score': round(academic_score, 1),
                'attendance_score': round(attendance_score, 1),
                'lms_score': round(lms_score, 1),
                'placement_score': round(placement_score, 1),
                'skills_engagement_score': round(skills_eng_score, 1),
            },
            'positive_factors': positive_factors,
            'risk_flags': risk_flags,
            'recommended_interventions': recommended_interventions
        }

        return {
            'overall_success_score': overall_success_score,
            'academic_risk_level': risk_level,
            'placement_readiness_score': round(placement_score, 1),
            'placement_risk_level': placement_risk_level,
            'segment': segment,
            'explanation_json': explanation_json
        }

    @classmethod
    def evaluate_and_save_snapshot(cls, student: StudentProfile, auto_create_intervention=True):
        """Calculate metrics and upsert the current-day snapshot for a student."""
        metrics = cls.calculate_student_success_score(student)
        
        snapshot, _created = StudentSuccessSnapshot.objects.update_or_create(
            student=student,
            snapshot_date=timezone.localdate(),
            defaults={
                'overall_success_score': metrics['overall_success_score'],
                'academic_risk_level': metrics['academic_risk_level'],
                'placement_readiness_score': metrics['placement_readiness_score'],
                'placement_risk_level': metrics['placement_risk_level'],
                'segment': metrics['segment'],
                'explanation_json': metrics['explanation_json'],
            },
        )

        # Trigger Automated Intervention Record if High/Critical Risk
        if auto_create_intervention and metrics['academic_risk_level'] in [StudentSuccessSnapshot.RiskLevel.HIGH, StudentSuccessSnapshot.RiskLevel.CRITICAL]:
            rec_types = metrics['explanation_json'].get('recommended_interventions', [])
            primary_type = rec_types[0] if rec_types else InterventionRecord.InterventionType.ACADEMIC_TUTORING
            
            # Check if active intervention already exists
            existing_active = InterventionRecord.objects.filter(
                student=student,
                status__in=[InterventionRecord.Status.PROPOSED, InterventionRecord.Status.IN_PROGRESS]
            ).exists()

            if not existing_active:
                assigned_by = student.department.assigned_faculty.first().faculty_user if student.department.assigned_faculty.exists() else None
                if not assigned_by:
                    from django.contrib.auth import get_user_model
                    assigned_by = get_user_model().objects.filter(is_superuser=True).first()

                if assigned_by:
                    risk_reasons = ", ".join(metrics['explanation_json']['risk_flags']) or "Low composite success score."
                    InterventionRecord.objects.create(
                        student=student,
                        assigned_by=assigned_by,
                        assigned_to=assigned_by,
                        intervention_type=primary_type,
                        reason=f"Automated AI Risk Flag ({metrics['academic_risk_level']}): {risk_reasons}",
                        status=InterventionRecord.Status.PROPOSED,
                        follow_up_date=timezone.now().date() + timedelta(days=14)
                    )

        return snapshot

    @classmethod
    def evaluate_all_students(cls):
        """Evaluates and updates analytics snapshots for all active students."""
        active_students = StudentProfile.objects.filter(enrollment_status=StudentProfile.EnrollmentStatus.ACTIVE)
        updated_snapshots = []
        with transaction.atomic():
            for student in active_students:
                snapshot = cls.evaluate_and_save_snapshot(student)
                updated_snapshots.append(snapshot)
        return len(updated_snapshots)
