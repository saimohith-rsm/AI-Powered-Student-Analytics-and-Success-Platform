from django.core.management.base import BaseCommand
from apps.students.services import SyntheticDataGeneratorService

class Command(BaseCommand):
    help = 'Generates realistic synthetic demonstration data for Smart Campus Analytics.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=40,
            help='Number of synthetic students to generate (default: 40)'
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for reproducible synthetic generation (default: 42)'
        )

    def handle(self, *args, **options):
        count = options['count']
        seed = options['seed']
        self.stdout.write(self.style.NOTICE(f"Generating synthetic data for {count} students across Groups A-F (Seed: {seed})..."))
        created_count = SyntheticDataGeneratorService.generate_all(student_count=count, seed=seed)
        self.stdout.write(self.style.SUCCESS(f"Successfully generated demo data for {created_count} students with full academic, attendance, LMS, placement, and intervention records!"))
