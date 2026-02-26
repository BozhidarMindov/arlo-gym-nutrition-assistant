from langchain.tools import tool
from markdown_pdf import MarkdownPdf, Section

from db_operations import (
    add_sets,
    create_workout,
    delete_last_workout_with_sets,
    get_exercise_series,
    get_last_workout_with_sets,
)
from utils import build_file_path, merge_set_notes, normalize_date_input
from workout_validation import validate_and_normalize_workout_payload


@tool
def save_to_md_file(content: str) -> str:
    """Save Markdown content to a temp file. Returns the file path.

    Args:
        content (str): Markdown content.

    Returns:
        str: File path.
    """
    path = build_file_path(".md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


@tool
def save_to_txt_file(content: str) -> str:
    """Save text content to a temp TXT file. Returns the file path.

    Args:
        content (str): Text content.

    Returns:
        str: File path.
    """
    path = build_file_path(".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


@tool
def save_to_pdf_file(content: str) -> str:
    """Save Markdown content to a temp PDF. Returns the file path.

    Args:
        content (str): Markdown content.

    Returns:
        str: File path.
    """
    path = build_file_path(".pdf")
    pdf = MarkdownPdf(toc_level=0)
    pdf.add_section(Section(content, toc=False))
    pdf.save(path)
    return path


@tool
def log_workout(workout: dict) -> str:
    """Log one workout using this schema:

    {
      "workout_date": "YYYY-MM-DD|today|yesterday|tomorrow",
      "notes": "optional",
      "entries": [
        {
          "exercise_name": "Bench Press",
          "sets": [{"set_number": 1, "reps": 8, "weight": 60, "notes": "optional"}]
        }
      ]
    }

    Args:
        workout (dict): Workout.

    Returns:
        str: A logged workout message.
    """
    if not isinstance(workout, dict):
        return "Invalid workout payload: workout must be an object."

    payload = dict(workout)
    payload["workout_date"] = normalize_date_input(str(payload.get("workout_date", "")))
    try:
        normalized = validate_and_normalize_workout_payload(payload)
    except ValueError as exc:
        return f"Invalid workout payload: {exc}"

    workout_id = create_workout(
        workout_date=normalized.workout_date, notes=normalized.notes or ""
    )

    exercise_count = 0
    set_count = 0
    for entry in normalized.entries:
        set_rows = []
        for i, s in enumerate(entry.sets, start=1):
            set_rows.append(
                {
                    "set_number": s.set_number or i,
                    "reps": s.reps,
                    "weight": s.weight,
                    "duration_minutes": s.duration_minutes,
                    "distance_km": s.distance_km,
                    "notes": merge_set_notes(s.notes),
                }
            )

        add_sets(
            workout_id=workout_id, exercise_name=entry.exercise_name, set_rows=set_rows
        )
        exercise_count += 1
        set_count += len(set_rows)

    return f"Logged workout #{workout_id} on {normalized.workout_date} with {exercise_count} exercises and {set_count} sets."


@tool
def get_exercise_progress(exercise_name: str, limit: int = 200) -> str:
    """Return date-ordered set history for one exercise.

    Args:
        exercise_name (str): Exercise name.
        limit (int, optional): Limit the number of sets to return. Defaults to 200.

    Returns:
        str: A date-ordered set history message.
    """
    rows = get_exercise_series(exercise_name=exercise_name, limit=limit)
    if not rows:
        return f"No logged sets found for {exercise_name}."

    lines = []
    for workout_date, reps, weight, duration_minutes, distance_km in rows:
        reps_text = f"{reps} reps" if reps is not None else "reps n/a"
        weight_text = f"{weight}" if weight is not None else "weight n/a"
        duration_text = (
            f"{duration_minutes} min"
            if duration_minutes is not None
            else "duration n/a"
        )
        distance_text = (
            f"{distance_km} km" if distance_km is not None else "distance n/a"
        )
        lines.append(
            f"{workout_date}: {reps_text}, {weight_text}, {duration_text}, {distance_text}"
        )
    return "\n".join(lines)


@tool
def get_last_workout(request: str) -> str:
    """Return raw DB data for the most recent workout and all its sets.

    Args:
        request (str): Must be "last_workout".

    Returns:
        str: Raw DB data for the most recent workout and all its sets in string form.
    """
    if not request or not str(request).strip():
        return "Missing request. Use request='last_workout'."

    workout, sets = get_last_workout_with_sets()
    if workout is None:
        return "No workouts logged yet."
    return str({"workout": workout, "sets": sets})


@tool
def delete_last_workout(request: str) -> str:
    """Delete the most recent workout and all related sets.

    Args:
        request (str): Must be "delete_last_workout" (or "confirm").

    Returns:
        str: A message about deletion.
    """
    if (request or "").strip().lower() not in {"delete_last_workout", "confirm"}:
        return "Missing confirmation. Use request='delete_last_workout'."

    deleted = delete_last_workout_with_sets()
    if deleted is None:
        return "No workouts logged yet."

    return f"Deleted workout #{deleted['id']} from {deleted['workout_date']} and {deleted['deleted_sets']} related sets."
