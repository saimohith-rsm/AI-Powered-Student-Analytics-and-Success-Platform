"""Query helpers for analytics records, keeping dashboards on current snapshots."""
from django.db.models import OuterRef, Subquery

from apps.analytics.models import StudentSuccessSnapshot


def latest_snapshots(queryset=None):
    """Return at most one (latest date, then highest PK) snapshot per student.

    The supplied queryset can carry role/department scoping; the correlated
    subquery ensures an older high-risk snapshot does not override a newer one.
    """
    if queryset is None:
        queryset = StudentSuccessSnapshot.objects.all()
    latest_pk = (
        StudentSuccessSnapshot.objects.filter(student_id=OuterRef("student_id"))
        .order_by("-snapshot_date", "-pk")
        .values("pk")[:1]
    )
    return queryset.filter(pk=Subquery(latest_pk))
