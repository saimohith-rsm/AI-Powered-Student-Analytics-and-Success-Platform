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

            # Ensure baseline superuser exists if none exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(is_superuser=True).exists():
                admin_username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
                admin_email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@smartcampus.edu")
                admin_password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin@12345")
                User.objects.create_superuser(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                    role="ADMIN",
                )
                sys.stderr.write(f"[DB Init] Created default admin account: {admin_username}\n")

            _initialized = True
            return True
        except Exception as exc:
            sys.stderr.write(f"[DB Init] Database initialization warning: {exc}\n")
            logger.warning("Database initialization warning: %s", exc)
            return False
