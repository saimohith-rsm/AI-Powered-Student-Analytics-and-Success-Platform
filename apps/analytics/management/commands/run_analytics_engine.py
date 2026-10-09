from django.core.management.base import BaseCommand
from apps.analytics.services import StudentAnalyticsEngine

class Command(BaseCommand):
    help = 'Executes the AI Analytics Engine to calculate student success scores, risk levels, and automated interventions.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running AI Analytics & Risk Engine for all active students..."))
        count = StudentAnalyticsEngine.evaluate_all_students()
        self.stdout.write(self.style.SUCCESS(f"Successfully calculated explainable success scores and updated snapshots for {count} students!"))
