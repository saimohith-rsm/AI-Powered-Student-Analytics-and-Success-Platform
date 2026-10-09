from rest_framework import serializers
from apps.analytics.models import StudentSuccessSnapshot
from apps.students.models import StudentProfile

class StudentSuccessSnapshotSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    department_code = serializers.CharField(source='student.department.code', read_only=True)
    risk_level_display = serializers.CharField(source='get_academic_risk_level_display', read_only=True)

    class Meta:
        model = StudentSuccessSnapshot
        fields = [
            'id',
            'student_id',
            'student_name',
            'department_code',
            'snapshot_date',
            'overall_success_score',
            'academic_risk_level',
            'risk_level_display',
            'placement_readiness_score',
            'placement_risk_level',
            'segment',
            'explanation_json'
        ]
