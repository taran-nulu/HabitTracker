"""Persistence layer: locates the data file and reads/writes it atomically.

Data lives in the standard macOS location so the app works identically whether
it is run from source or from inside a py2app bundle (a bundle's own directory
is read-only-ish and gets replaced on every rebuild).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

APP_DIR_NAME = "HabitTracker"
DATA_FILENAME = "data.json"
SCHEMA_VERSION = 1


def data_dir() -> Path:
    """Return the app's support directory, creating it if needed."""
    path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def data_file() -> Path:
    return data_dir() / DATA_FILENAME


def empty_payload() -> dict:
    return {"version": SCHEMA_VERSION, "habits": [], "completions": {}}


def _coerce(raw: object) -> dict:
    """Normalize loaded JSON into the expected shape, dropping junk."""
    if not isinstance(raw, dict):
        return empty_payload()

    payload = empty_payload()
    payload["version"] = SCHEMA_VERSION

    habits = raw.get("habits")
    if isinstance(habits, list):
        seen: set[str] = set()
        for item in habits:
            if not isinstance(item, dict):
                continue
            hid = item.get("id")
            name = item.get("name")
            if not isinstance(hid, str) or not hid or hid in seen:
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            seen.add(hid)
            payload["habits"].append(
                {
                    "id": hid,
                    "name": name.strip(),
                    "color": item.get("color") if isinstance(item.get("color"), str) else None,
                    "created": item.get("created") if isinstance(item.get("created"), str) else None,
                }
            )

    completions = raw.get("completions")
    if isinstance(completions, dict):
        for hid, dates in completions.items():
            if not isinstance(hid, str) or not isinstance(dates, list):
                continue
            good = sorted({d for d in dates if isinstance(d, str) and len(d) == 10})
            if good:
                payload["completions"][hid] = good

    # Drop completion history for habits that no longer exist.
    payload["completions"] = {
        hid: dates for hid, dates in payload["completions"].items() if hid in seen
    }
    return payload


def load() -> dict:
    """Load persisted data.

    A missing file yields empty data. A corrupt file is set aside as
    ``data.json.corrupt`` and empty data is returned, so a bad write can never
    make the app fail to start.
    """
    path = data_file()
    if not path.exists():
        return empty_payload()

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        try:
            shutil.copy2(path, path.with_name(DATA_FILENAME + ".corrupt"))
        except OSError:
            pass
        return empty_payload()

    return _coerce(raw)


def save(payload: dict) -> None:
    """Write data atomically: a temp file in the same dir, then ``os.replace``.

    ``os.replace`` is atomic on macOS, so an interrupted save (crash, force
    quit, power loss) can never leave a half-written file behind.
    """
    path = data_file()
    directory = path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".data-", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise