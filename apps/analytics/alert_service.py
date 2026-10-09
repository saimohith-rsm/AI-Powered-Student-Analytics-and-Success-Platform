"""Student Risk Alert Email Service.

Handles automated and counselor-triggered email notifications for students identified
with CRITICAL or HIGH academic, attendance, or placement risk.
"""
import logging
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.students.models import StudentProfile
from apps.analytics.models import StudentSuccessSnapshot
from apps.interventions.models import InterventionRecord

logger = logging.getLogger(__name__)


class StudentRiskAlertService:
    """Service to format and send risk notification alerts to students and advisors."""

    @classmethod
    def get_latest_risk_info(cls, student: StudentProfile) -> Dict[str, Any]:
        """Fetch the most recent success snapshot and risk factors for a student."""
        snapshot = (
            StudentSuccessSnapshot.objects.filter(student=student)
            .order_by("-snapshot_date", "-id")
            .first()
        )
        if not snapshot:
            return {
                "risk_level": "UNKNOWN",
                "success_score": "N/A",
                "risk_flags": ["No analytics snapshot computed yet"],
                "positive_factors": [],
                "snapshot": None,
            }

        explanation = snapshot.explanation_json or {}
        risk_flags = explanation.get("risk_flags", [])
        positive_factors = explanation.get("positive_factors", [])

        return {
            "risk_level": snapshot.academic_risk_level,
            "success_score": f"{snapshot.overall_success_score:.1f}",
            "risk_flags": risk_flags,
            "positive_factors": positive_factors,
            "snapshot": snapshot,
        }

    @classmethod
    def compose_alert_message(
        cls,
        student: StudentProfile,
        risk_info: Dict[str, Any],
        sender_name: str,
        custom_note: Optional[str] = None,
    ) -> Dict[str, str]:
        """Compose subject and formatted body for the student alert email."""
        risk_level = risk_info.get("risk_level", "HIGH")
        score = risk_info.get("success_score", "N/A")
        flags = risk_info.get("risk_flags", [])

        subject = (
            f"[{risk_level} RISK ALERT] Academic & Attendance Advisory - {student.full_name} ({student.student_id})"
        )

        flags_text = "\n".join([f"  • {flag}" for flag in flags]) if flags else "  • Composite score below academic safety threshold"

        custom_text = f"\nFaculty Counselor Note:\n\"{custom_note}\"\n" if custom_note else ""

        body = f"""Dear {student.full_name},

This is an automated advisory notification from the Smart Campus Analytics System issued by {sender_name}.

Our continuous student success monitoring has identified that your profile currently stands in the {risk_level} RISK category with an overall composite success score of {score} / 100.

Triggering Risk Factors:
{flags_text}
{custom_text}
Next Recommended Actions:
1. Schedule a guidance session with your Department Academic Advisor ({student.department.name}).
2. Attend scheduled remedial tutoring and skill improvement sessions.
3. Review your attendance and LMS assignment submission logs on the student portal.

We are committed to helping you succeed in your academic and career journey. Please reach out to your faculty mentor or reply to this advisory as soon as possible.

Best regards,
Smart Campus Analytics & Student Success Team
Department of {student.department.name}
"""
        return {"subject": subject, "body": body}

    @classmethod
    def send_individual_alert(
        cls,
        student: StudentProfile,
        sender_user,
        custom_note: Optional[str] = None,
        create_intervention: bool = True,
    ) -> Dict[str, Any]:
        """Send a personalized risk advisory email to a single student."""
        risk_info = cls.get_latest_risk_info(student)
        risk_level = risk_info.get("risk_level", "HIGH")

        sender_name = sender_user.get_full_name() or sender_user.username
        composed = cls.compose_alert_message(student, risk_info, sender_name, custom_note)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "alerts@smartcampus.edu")
        recipient_list = [student.email] if student.email else []

        if not recipient_list:
            logger.warning("Failed to send risk alert: Student %s has no email address.", student.student_id)
            return {
                "success": False,
                "student_id": student.student_id,
                "error": "Student has no email address configured.",
            }

        try:
            send_mail(
                subject=composed["subject"],
                message=composed["body"],
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            logger.info("Sent %s risk alert email to student %s (%s)", risk_level, student.student_id, student.email)

            if create_intervention:
                # Log an intervention record so counseling progress is tracked
                reason_summary = f"Risk alert email dispatched ({risk_level} Risk, Score {risk_info.get('success_score')})"
                if custom_note:
                    reason_summary += f" | Note: {custom_note}"

                InterventionRecord.objects.create(
                    student=student,
                    assigned_by=sender_user,
                    assigned_to=sender_user,
                    intervention_type=InterventionRecord.InterventionType.ACADEMIC_TUTORING
                    if "academic" in str(risk_info.get("risk_flags", [])).lower()
                    else InterventionRecord.InterventionType.ATTENDANCE_COUNSELING,
                    reason=reason_summary[:250],
                    status=InterventionRecord.Status.IN_PROGRESS,
                    follow_up_date=timezone.now().date(),
                    outcome_notes=f"Automated email alert delivered to {student.email} on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                )

            return {
                "success": True,
                "student_id": student.student_id,
                "student_name": student.full_name,
                "email": student.email,
                "risk_level": risk_level,
                "score": risk_info.get("success_score"),
            }

        except Exception as exc:
            logger.exception("Failed to send risk alert email to %s: %s", student.student_id, exc)
            return {
                "success": False,
                "student_id": student.student_id,
                "error": str(exc),
            }

    @classmethod
    def send_batch_alerts(
        cls,
        students,
        sender_user,
        custom_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send email alerts to all provided at-risk students."""
        sent_count = 0
        failed_count = 0
        details = []

        for student in students:
            res = cls.send_individual_alert(
                student=student,
                sender_user=sender_user,
                custom_note=custom_note,
                create_intervention=True,
            )
            if res.get("success"):
                sent_count += 1
            else:
                failed_count += 1
            details.append(res)

        return {
            "total": len(students),
            "sent": sent_count,
            "failed": failed_count,
            "details": details,
        }
