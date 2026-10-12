"""py2app build script.

Produces a self-contained, double-clickable `Habit Tracker.app` that runs from
the Dock. Build with `make build` (or `python setup.py py2app`).
"""

from pathlib import Path

from setuptools import setup

APP = ["main.py"]

DATA_FILES = []

OPTIONS = {
    # argv_emulation lets a double-clicked .app handle files/URLs, but it adds
    # an Open Apple Event handler that can swallow clicks in a Tk app. We do not
    # accept dropped files, so keep it off.
    "argv_emulation": False,
    # `habit_tracker` is our own local package: py2app does not follow local
    # imports automatically, so it must be listed or the bundle fails on launch.
    # `customtkinter` ships themes/font via plain open() relative to __file__,
    # so it must be included as real files rather than a zip.
    "packages": ["habit_tracker", "customtkinter"],
    "includes": ["tkinter", "tkinter.ttk", "tkinter.font", "tkinter.messagebox"],
    "iconfile": "HabitTracker.icns",
    "plist": {
        "CFBundleName": "Habit Tracker",
        "CFBundleDisplayName": "Habit Tracker",
        "CFBundleIdentifier": "com.habittracker.app",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleIconFile": "HabitTracker.icns",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        # Data lives in ~/Library/Application Support/HabitTracker, so the app never
# needs to write inside its own bundle.
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHumanReadableCopyright": "",
    },
}


def _require_icon() -> None:
    if not Path("HabitTracker.icns").exists():
        raise SystemExit(
            "HabitTracker.icns is missing. Run `make icon` (or tools/make_icon.sh) first."
        )


_require_icon()

setup(
    name="HabitTracker",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)