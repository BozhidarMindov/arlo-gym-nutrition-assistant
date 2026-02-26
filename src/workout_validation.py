from dataclasses import dataclass
from datetime import date
from typing import Any, List, Optional


@dataclass
class SetEntry:
    set_number: Optional[int] = None
    reps: Optional[int] = None
    weight: Optional[float] = None
    duration_minutes: Optional[float] = None
    distance_km: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ExerciseEntry:
    exercise_name: str
    sets: List[SetEntry]


@dataclass
class WorkoutLog:
    workout_date: str  # YYYY-MM-DD
    notes: Optional[str]
    entries: List[ExerciseEntry]


def _ensure_int(x: Any) -> Optional[int]:
    """Ensures that the input is an integer or None.

    Args:
        x (Any): The input to ensure it is an integer or None.

    Returns:
        Optional[int]: The input if it is an integer or None.
    """
    if x is None or isinstance(x, bool):
        return None
    try:
        return int(x)
    except Exception:
        return None


def _ensure_float(x: Any) -> Optional[float]:
    """Ensures that the input is a float or None.

    Args:
        x (Any): The input to ensure it is a float or None.

    Returns:
        Optional[float]: The input if it is a float or None.
    """
    if x is None or isinstance(x, bool):
        return None
    try:
        return float(x)
    except Exception:
        return None


def validate_and_normalize_workout_payload(data: Any) -> WorkoutLog:
    """Validates and normalizes the workout payload.

    Args:
        data (Any): The workout payload.

    Returns:
        WorkoutLog: The normalized workout payload.
    """
    if not isinstance(data, dict):
        raise ValueError("Workout must be a JSON object.")

    workout_date = str(data.get("workout_date", "")).strip()
    if not workout_date:
        raise ValueError("Missing workout_date (YYYY-MM-DD).")
    try:
        date.fromisoformat(workout_date)
    except ValueError as e:
        raise ValueError("workout_date must be YYYY-MM-DD.") from e

    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise ValueError("entries must be a non-empty list.")

    entries: List[ExerciseEntry] = []
    for ex in entries_raw:
        if not isinstance(ex, dict):
            continue

        name = str(ex.get("exercise_name", "")).strip()
        if not name:
            continue

        sets_raw = ex.get("sets")
        if not isinstance(sets_raw, list) or not sets_raw:
            raise ValueError(f"Exercise '{name}' has no sets.")

        sets: List[SetEntry] = []
        for s in sets_raw:
            if not isinstance(s, dict):
                continue

            set_number = _ensure_int(s.get("set_number"))
            reps = _ensure_int(s.get("reps"))
            weight = _ensure_float(s.get("weight"))
            duration = _ensure_float(s.get("duration_minutes"))
            distance = _ensure_float(s.get("distance_km"))

            if set_number is not None and (set_number <= 0 or set_number > 1000):
                raise ValueError(f"Unreasonable set_number value in '{name}'.")
            if reps is not None and (reps < 0 or reps > 100):
                raise ValueError(f"Unreasonable reps value in '{name}'.")
            if weight is not None and (weight < 0 or weight > 500):
                raise ValueError(f"Unreasonable weight value in '{name}'.")
            if duration is not None and (duration < 0 or duration > 600):
                raise ValueError(f"Unreasonable duration value in '{name}'.")
            if distance is not None and (distance < 0 or distance > 200):
                raise ValueError(f"Unreasonable distance value in '{name}'.")

            notes = s.get("notes")
            if notes is not None:
                notes = str(notes).strip() or None

            has_metrics = any(v is not None for v in (reps, weight, duration, distance))
            if not has_metrics:
                raise ValueError(
                    f"A set in '{name}' is missing metrics (reps/weight/duration/distance)."
                )

            sets.append(
                SetEntry(
                    set_number=set_number,
                    reps=reps,
                    weight=weight,
                    duration_minutes=duration,
                    distance_km=distance,
                    notes=notes,
                )
            )

        if not sets:
            raise ValueError(f"Exercise '{name}' has no valid sets.")

        entries.append(ExerciseEntry(exercise_name=name, sets=sets))

    if not entries:
        raise ValueError("No valid exercises found.")

    return WorkoutLog(
        workout_date=workout_date,
        notes=str(data.get("notes", "")).strip() or None,
        entries=entries,
    )
