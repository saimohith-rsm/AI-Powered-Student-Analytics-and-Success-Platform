"""Database initialization hook for serverless environments (e.g., Vercel)
and fresh database deployments.
"""
import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

_initialized = False
_lock = threading.Lock()


def ensure_database_initialized() -> bool:
    """Ensure database tables and baseline lookup data exist.

    Safe for serverless environments like Vercel where SQLite in /tmp starts
    empty on cold starts, as well as fresh cloud Postgres instances.
    Guarded by an in-memory lock to only execute once per worker process.
    """
    global _initialized
    if _initialized:
        return True

    with _lock:
        if _initialized:
            return True

        try:
            from django.db import connection
            from django.core.management import call_command

            # Fast table check
            existing_tables = set(connection.introspection.table_names())
            needs_migration = (
                "students_department" not in existing_tables
                or "accounts_user" not in existing_tables
            )

            if needs_migration:
                sys.stderr.write("[DB Init] Missing database tables detected. Running migrations...\n")
                call_command("migrate", interactive=False)
                sys.stderr.write("[DB Init] Migrations applied successfully.\n")

            # Seed baseline departments, programs, and academic calendar if missing
            from apps.students.models import Department, Program, AcademicYear, Semester
            if not Department.objects.exists():
                sys.stderr.write("[DB Init] Seeding baseline departments and academic calendar...\n")
                departments_data = [
                    ('CSE', 'Computer Science & Engineering', 'Dr. Alan Turing'),
                    ('ECE', 'Electronics & Communication', 'Dr. Claude Shannon'),
                    ('EEE', 'Electrical & Electronics', 'Dr. Nikola Tesla'),
                    ('MECH', 'Mechanical Engineering', 'Dr. James Watt'),
                ]
                for code, name, hod in departments_data:
                    dept, _ = Department.objects.get_or_create(
                        code=code, defaults={'name': name, 'head_of_department': hod}
                    )
                    Program.objects.get_or_create(
                        code=f"BTECH-{code}",
                        defaults={'name': f"B.Tech in {name}", 'department': dept},
                    )

                acad_year, _ = AcademicYear.objects.get_or_create(
                    year_label="2025-2026", defaults={'is_current': True}
                )
                for num in range(1, 9):
                    Semester.objects.get_or_create(
                        number=num, academic_year=acad_year, defaults={'is_active': (num == 5)}
                    )

            # Ensure baseline demo accounts exist (Admin, Faculty, Placement, Student)
            from django.contrib.auth import get_user_model
            from apps.students.models import FacultyAssignment, StudentProfile
            User = get_user_model()

            # 1. Primary Admin Account
            admin_user, _ = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@smartcampus.edu",
                    "role": User.Role.ADMINISTRATOR,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            admin_user.set_password(os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin@1234"))
            admin_user.save()

            # 2. Custom Admin Account (sindhu861)
            sindhu_user, _ = User.objects.get_or_create(
                username="sindhu861",
                defaults={
                    "email": "sindhu861@smartcampus.edu",
                    "role": User.Role.ADMINISTRATOR,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            sindhu_user.set_password("sindhu@861")
            sindhu_user.save()

            # 3. Faculty Account (faculty_cse)
            cse_dept = Department.objects.filter(code="CSE").first()
            faculty_user, _ = User.objects.get_or_create(
                username="faculty_cse",
                defaults={
                    "email": "faculty@smartcampus.edu",
                    "role": User.Role.FACULTY,
                    "department_name": "CSE",
                    "is_staff": True,
                },
            )
            faculty_user.set_password("Faculty@1234")
            faculty_user.save()
            if cse_dept:
                FacultyAssignment.objects.get_or_create(faculty_user=faculty_user, department=cse_dept)

            # 4. Placement Officer (placement_officer)
            placement_user, _ = User.objects.get_or_create(
                username="placement_officer",
                defaults={
                    "email": "placement@smartcampus.edu",
                    "role": User.Role.PLACEMENT_OFFICER,
                    "is_staff": True,
                },
            )
            placement_user.set_password("Placement@1234")
            placement_user.save()

            # 5. Demo Student Account (stu2025001)
            stu_user, _ = User.objects.get_or_create(
                username="stu2025001",
                defaults={
                    "email": "stu2025001@smartcampus.edu",
                    "first_name": "Aarav",
                    "last_name": "Sharma",
                    "role": User.Role.STUDENT,
                },
            )
            stu_user.set_password("Student@1234")
            stu_user.save()
            if cse_dept:
                prog = cse_dept.programs.first()
                StudentProfile.objects.get_or_create(
                    student_id="STU2025001",
                    defaults={
                        "user": stu_user,
                        "first_name": "Aarav",
                        "last_name": "Sharma",
                        "email": stu_user.email,
                        "department": cse_dept,
                        "program": prog,
                        "admission_year": 2025,
                        "current_semester": 5,
                    },
                )

            _initialized = True
            return True
        except Exception as exc:
            sys.stderr.write(f"[DB Init] Database initialization warning: {exc}\n")
            logger.warning("Database initialization warning: %s", exc)
            return False
