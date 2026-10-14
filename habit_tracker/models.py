"""Habit data model and in-memory store."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import storage

# Accent colors cycled through when the user does not pick one.
PALETTE = [
    "#4C8DFF",  # blue
    "#22B07D",  # green
    "#E5A13A",  # amber
    "#E0575B",  # red
    "#9B6DF2",  # purple
    "#12A5B8",  # teal
    "#E07AB8",  # pink
    "#8AB543",  # lime
    "#F0743B",  # orange
    "#5A6B8C",  # slate
]


def _is_hex_color(value: str) -> bool:
    """True for a #rrggbb color, which is what Tk widgets accept."""
    if not isinstance(value, str) or not value.startswith("#"):
        return False
    return len(value) == 7 and all(c in "0123456789abcdefABCDEF" for c in value[1:])


def normalize_color(value: str | None, fallback: str) -> str:
    """Coerce a stored/user color to #rrggbb, falling back when invalid."""
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate.startswith("#"):
            candidate = "#" + candidate
        if _is_hex_color(candidate):
            return candidate.upper()
    return fallback


@dataclass
class Habit:
    id: str
    name: str
    color: str
    created: date = field(default_factory=date.today)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created": self.created.isoformat(),
        }


class Store:
    """Holds habits and their completion history, and persists on demand."""

    def __init__(self) -> None:
        self.habits: list[Habit] = []
        # habit_id -> set of ISO date strings that were completed
        self._done: dict[str, set[str]] = {}

    # ---------------------------------------------------------------- load

    def load(self) -> None:
        payload = storage.load()
        self.habits = []
        self._done = {}

        for item in payload.get("habits", []):
            created_raw = item.get("created")
            try:
                created = date.fromisoformat(created_raw) if created_raw else date.today()
            except ValueError:
                created = date.today()

            color = normalize_color(item.get("color"), self._next_color())

            self.habits.append(
                Habit(id=item["id"], name=item["name"], color=color, created=created)
            )

        for hid, dates in payload.get("completions", {}).items():
            self._done[hid] = set(dates)

    def to_payload(self) -> dict:
        return {
            "version": storage.SCHEMA_VERSION,
            "habits": [h.to_dict() for h in self.habits],
            "completions": {
                hid: sorted(dates) for hid, dates in self._done.items() if dates
            },
        }

    def save(self) -> None:
        storage.save(self.to_payload())

    # --------------------------------------------------------------- habits

    def _next_color(self) -> str:
        """Pick a palette color that is least used so far."""
        used = [h.color for h in self.habits]
        counts = {c: used.count(c) for c in PALETTE}
        return min(counts, key=lambda c: counts[c])

    def add_habit(self, name: str, color: str | None = None) -> Habit:
        name = name.strip()
        if not name:
            raise ValueError("Habit name cannot be empty")
        habit = Habit(
            id=uuid.uuid4().hex,
            name=name,
            # No color given, or an unusable one, falls back to the automatic
            # least-used palette entry.
            color=normalize_color(color, self._next_color()),
            created=date.today(),
        )
        self.habits.append(habit)
        return habit

    def get(self, habit_id: str) -> Habit | None:
        for habit in self.habits:
            if habit.id == habit_id:
                return habit
        return None

    def rename_habit(self, habit_id: str, name: str) -> None:
        habit = self.get(habit_id)
        if habit is None:
            raise ValueError("Unknown habit")
        name = name.strip()
        if not name:
            raise ValueError("Habit name cannot be empty")
        habit.name = name

    def set_color(self, habit_id: str, color: str) -> None:
        """Change a habit's accent color.

        Accepts any #rrggbb value so the user is not restricted to the
        built-in palette; falls back to automatic assignment if invalid.
        """
        habit = self.get(habit_id)
        if habit is None:
            raise ValueError("Unknown habit")
        if not _is_hex_color(color):
            raise ValueError("Color must be a hex value like #4C8DFF")
        habit.color = color

    def delete_habit(self, habit_id: str) -> None:
        """Remove a habit and its completion history."""
        self.habits = [h for h in self.habits if h.id != habit_id]
        self._done.pop(habit_id, None)

    def move_habit(self, habit_id: str, direction: int) -> None:
        """Shift a habit up (-1) or down (+1) in the display order."""
        index = next((i for i, h in enumerate(self.habits) if h.id == habit_id), None)
        if index is None:
            return
        target = index + direction
        if 0 <= target < len(self.habits):
            self.habits[index], self.habits[target] = self.habits[target], self.habits[index]

    # ---------------------------------------------------------- completions

    def is_done(self, habit_id: str, day: date) -> bool:
        return day.isoformat() in self._done.get(habit_id, ())

    def toggle(self, habit_id: str, day: date) -> bool:
        """Flip a day's completion. Returns the new state."""
        key = day.isoformat()
        days = self._done.setdefault(habit_id, set())
        if key in days:
            days.discard(key)
            return False
        days.add(key)
        return True

    def done_dates(self, habit_id: str) -> set[str]:
        return set(self._done.get(habit_id, ()))

    def completion_count(self, habit_id: str, year: int, month: int) -> int:
        prefix = f"{year:04d}-{month:02d}"
        return sum(1 for d in self._done.get(habit_id, ()) if d.startswith(prefix))

    # -------------------------------------------------------------- streaks

    def current_streak(self, habit_id: str, today: date | None = None) -> int:
        """Consecutive completed days ending today (or yesterday if today is open).

        Allowing the streak to survive an as-yet-unfinished today matches how
        people read a streak: it only breaks once a whole day is missed.
        """
        today = today or date.today()
        done = self._done.get(habit_id)
        if not done:
            return 0

        cursor = today
        if cursor.isoformat() not in done:
            cursor = today - timedelta(days=1)
        if cursor.isoformat() not in done:
            return 0

        streak = 0
        while cursor.isoformat() in done:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def best_streak(self, habit_id: str) -> int:
        done = self._done.get(habit_id)
        if not done:
            return 0

        days = sorted(date.fromisoformat(d) for d in done)
        best = run = 1
        for prev, cur in zip(days, days[1:]):
            run = run + 1 if cur - prev == timedelta(days=1) else 1
            best = max(best, run)
        return best