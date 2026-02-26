import os
import re
import tempfile
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional


def generated_files_dir() -> Path:
    """
    Returns:
        Path: A temp directory for generated assistant files.
    """
    base_dir = os.environ.get("GRADIO_TEMP_DIR") or tempfile.gettempdir()
    path = Path(base_dir) / "arlo_files"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_file_path(extension: str) -> str:
    """Build a file path from an extension.

    Args:
        extension (str): The extension of the file.

    Returns:
        str: The file path.
    """
    return str(generated_files_dir() / f"{uuid.uuid4()}{extension}")


def normalize_date_input(date_text: str) -> str:
    """Normalize a date input.

    Args:
        date_text (str): The date to normalize.

    Returns:
        str: The normalized date.
    """
    raw = (date_text or "").strip().lower()
    today = date.today()

    if raw in {"today", "todays", "today's"}:
        return today.isoformat()
    if raw == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    if raw == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    return date_text


def merge_set_notes(notes: Optional[str]) -> Optional[str]:
    """Merge notes into a single string joined by |.

    Args:
        Optional[str]: The notes to merge.

    Returns:
        Optional[str]: The merged notes (or None if no notes).
    """
    parts: list[str] = []
    if notes:
        parts.append(str(notes))
    return " | ".join(parts) if parts else None
