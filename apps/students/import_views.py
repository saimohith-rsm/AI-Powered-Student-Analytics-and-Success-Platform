"""Secure web upload endpoint for CSV/Excel student datasets."""
import logging
import os
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect, render
from django.views import View

from apps.students.services import DataImportService
from config.storage_utils import get_upload_temp_dir

logger = logging.getLogger(__name__)
MAX_IMPORT_BYTES = 5 * 1024 * 1024


class DataImportWebUploadView(LoginRequiredMixin, View):
    """Admin-only dataset upload and validation interface."""
    template_name = "students/data_import.html"

    @staticmethod
    def _require_admin(user):
        if not user.is_admin_user():
            raise PermissionDenied("Only administrators can access the dataset import manager.")

    def get(self, request, *args, **kwargs):
        self._require_admin(request.user)
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        self._require_admin(request.user)
        dataset_file = request.FILES.get("dataset_file")

        if not dataset_file:
            messages.error(request, "Please select a CSV or Excel file to upload.")
            return redirect("students:data_import")
        if dataset_file.size > MAX_IMPORT_BYTES:
            messages.error(request, "The upload exceeds the 5 MB limit.")
            return redirect("students:data_import")

        original_name = Path(dataset_file.name).name
        ext = Path(original_name).suffix.lower()
        if ext not in {".csv", ".xlsx", ".xls"}:
            messages.error(request, "Unsupported file format. Upload a CSV or Excel (.xlsx, .xls) file.")
            return redirect("students:data_import")

        file_path = None
        try:
            import_dir = get_upload_temp_dir("imports")
            storage = FileSystemStorage(location=str(import_dir))
            filename = storage.save(original_name, dataset_file)
            file_path = storage.path(filename)

            result = DataImportService.import_from_file(file_path)
            imported_count = result.get("imported_count", 0)
            errors = result.get("errors", [])
            if imported_count:
                messages.success(request, f"Imported {imported_count} student records from '{original_name}'.")
            if errors:
                messages.warning(request, f"Encountered {len(errors)} validation issue(s) during import.")
            return render(request, self.template_name, {
                "filename": original_name, "imported_count": imported_count,
                "errors": errors, "import_completed": True,
            })
        except (ValueError, OSError) as exc:
            logger.warning("Student dataset import rejected: %s", exc)
            messages.error(request, "The file could not be imported. Check its format and required columns.")
            return redirect("students:data_import")
        except Exception:
            logger.exception("Unexpected failure while importing student dataset")
            messages.error(request, "Import failed due to an unexpected server error. Please contact the administrator.")
            return redirect("students:data_import")
        finally:
            if file_path:
                try:
                    os.remove(file_path)
                except (OSError, FileNotFoundError):
                    pass
