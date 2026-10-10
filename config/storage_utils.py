import logging
import os
import tempfile
import uuid
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def get_upload_temp_dir(subfolder: str = "imports") -> Path:
    """
    Return a guaranteed writable Path for temporary file uploads.
    Attempts settings.MEDIA_ROOT first, then falls back safely to
    the system temp directory (/tmp on Linux/Vercel/AWS Lambda) if
    MEDIA_ROOT is not writable.
    """
    candidates = []

    # 1. Configured MEDIA_ROOT
    try:
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root:
            candidates.append(Path(media_root) / subfolder)
    except Exception:
        pass

    # 2. System temporary directory (always writable on serverless /tmp)
    system_tmp = Path(tempfile.gettempdir())
    candidates.append(system_tmp / "smart_campus_uploads" / subfolder)
    candidates.append(system_tmp / subfolder)
    candidates.append(system_tmp)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / f".write_test_{uuid.uuid4().hex[:8]}"
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return candidate
        except (OSError, PermissionError) as exc:
            logger.debug("Directory %s is not writable (%s), attempting fallback...", candidate, exc)
            continue

    return system_tmp
