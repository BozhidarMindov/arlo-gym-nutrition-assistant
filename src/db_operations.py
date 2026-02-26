import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.environ.get("FITNESS_DB_PATH", "fitness.db")


@contextmanager
def get_conn():
    """Get a database connection."""
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                set_number INTEGER NOT NULL,
                reps INTEGER,
                weight REAL,
                duration_minutes REAL,
                distance_km REAL,
                notes TEXT,
                FOREIGN KEY(workout_id) REFERENCES workouts(id) ON DELETE CASCADE
            )
        """)


def create_workout(workout_date: str, notes: str = "") -> int:
    """Create a new workout with a given date and notes.

    Args:
        workout_date (str): The date of the workout.
        notes (str): The notes to add to the workout.

    Returns:
        int: The new workout id.
    """
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO workouts (workout_date, notes, created_at) VALUES (?, ?, ?)",
            (workout_date, notes or None, created_at),
        )
        return int(cur.lastrowid)


def add_sets(
    workout_id: int, exercise_name: str, set_rows: List[Dict[str, Any]]
) -> None:
    """Add sets to a workout.

    Args:
        workout_id (int): The workout id.
        exercise_name (str): The name of the exercise.
        set_rows (List[Dict[str, Any]]): The list of sets to add to the workout.

    Returns:
        None
    """
    with get_conn() as conn:
        for i, s in enumerate(set_rows, start=1):
            conn.execute(
                """
                INSERT INTO sets (
                    workout_id, exercise_name, set_number, reps, weight, duration_minutes, distance_km, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workout_id,
                    exercise_name,
                    int(s.get("set_number", i)),
                    s.get("reps"),
                    s.get("weight"),
                    s.get("duration_minutes"),
                    s.get("distance_km"),
                    s.get("notes"),
                ),
            )


def get_exercise_series(exercise_name: str, limit: int = 200) -> list:
    """Get an exercise series for a given exercise.

    Args:
        exercise_name (str): The name of the exercise.
        limit (int): The number of exercise series to get at most.

    Returns:
        list: The exercise series.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT w.workout_date, s.reps, s.weight, s.duration_minutes, s.distance_km
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            WHERE lower(s.exercise_name) = lower(?)
            ORDER BY w.workout_date ASC, s.set_number ASC
            LIMIT ?
            """,
            (exercise_name, limit),
        ).fetchall()
    return rows


def get_last_workout_with_sets() -> Tuple[
    Optional[Dict[str, Any]], List[Dict[str, Any]]
]:
    """Get the last workout with the sets in it.

    Returns:
        Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]: The last workout with the sets in it.
    """
    with get_conn() as conn:
        workout_row = conn.execute(
            """
            SELECT id, workout_date, notes, created_at
            FROM workouts
            ORDER BY id DESC, created_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not workout_row:
            return None, []

        workout = {
            "id": workout_row[0],
            "workout_date": workout_row[1],
            "notes": workout_row[2],
            "created_at": workout_row[3],
        }

        sets_rows = conn.execute(
            """
            SELECT exercise_name, set_number, reps, weight, duration_minutes, distance_km, notes
            FROM sets
            WHERE workout_id = ?
            ORDER BY id ASC
            """,
            (workout["id"],),
        ).fetchall()

    sets = [
        {
            "exercise_name": row[0],
            "set_number": row[1],
            "reps": row[2],
            "weight": row[3],
            "duration_minutes": row[4],
            "distance_km": row[5],
            "notes": row[6],
        }
        for row in sets_rows
    ]
    return workout, sets


def delete_last_workout_with_sets() -> Optional[Dict[str, Any]]:
    """Delete the last workout with the sets in it.

    Returns:
        Optional[Dict[str, Any]]: Info about the last workout with the sets in it.
    """
    with get_conn() as conn:
        workout_row = conn.execute(
            """
            SELECT id, workout_date, notes, created_at
            FROM workouts
            ORDER BY id DESC, created_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not workout_row:
            return None

        workout_id = int(workout_row[0])
        set_count_row = conn.execute(
            "SELECT COUNT(*) FROM sets WHERE workout_id = ?",
            (workout_id,),
        ).fetchone()
        set_count = int(set_count_row[0]) if set_count_row else 0

        conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    return {
        "id": workout_id,
        "workout_date": workout_row[1],
        "notes": workout_row[2],
        "created_at": workout_row[3],
        "deleted_sets": set_count,
    }


init_db()
