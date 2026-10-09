from django.core.management.base import BaseCommand, CommandError
from apps.students.services import DataImportService

class Command(BaseCommand):
    help = 'Imports student analytics datasets from a CSV or Excel file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the CSV or Excel dataset file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(self.style.NOTICE(f"Importing student dataset from {file_path}..."))

        try:
            result = DataImportService.import_from_file(file_path)
            imported_count = result['imported_count']
            errors = result['errors']

            self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} student records."))

            if errors:
                self.stdout.write(self.style.WARNING(f"\nEncountered {len(errors)} validation warnings/errors:"))
                for err in errors:
                    self.stdout.write(self.style.WARNING(f" - {err}"))
        except Exception as e:
            raise CommandError(f"Import failed: {str(e)}")
