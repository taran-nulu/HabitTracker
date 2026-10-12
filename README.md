# Habit Tracker

A macOS desktop habit tracker built with [CustomTkinter](https://github.com/tomschneum/customtkinter), packaged with [py2app](https://py2app.readthedocs.io/).

Habits are laid out as a month calendar — one row per habit, one column per day — so you can see at a glance what you have and haven't done.

## Features

- Month grid with click-to-toggle day cells
- Add, rename and delete habits (delete asks for confirmation)
- Current streak badge per habit
- Previous / next month navigation and a `Today` jump
- Dark / light theme toggle
- Progress saved automatically and restored on launch
- Launches from the Dock as a normal macOS app

## Requirements

- macOS 11 or newer
- Python 3.9+ (developed against 3.13)

## Run from source

```bash
make setup     # creates .venv and installs dependencies
make run       # launches the app
```

## Build the .app

```bash
make build     # -> dist/Habit Tracker.app
make install   # rebuilds, replaces the copy in /Applications, re-signs
```

After `make install`, open **Applications → Habit Tracker**. Right-click its icon in the Dock and choose **Options → Keep in Dock** to pin it permanently.

### Recompiling after changes

`make build` depends on `setup` and `icon`, so it reinstalls dependencies and regenerates the icon automatically before packaging. `make install` depends on `build`, so it covers everything in one step.

| You changed | Command |
| --- | --- |
| Python code (`habit_tracker/*.py`, `main.py`) | `make install` |
| `app_icon.PNG` | `make install` |
| `requirements.txt` | `make install` |
| `setup.py` (bundle name, version) | `make clean install` |

While iterating on code, `make run` is faster than a full rebuild — it launches straight from source and shares the same data file as the bundled app.

`make install` deletes the existing app in `/Applications` before copying, so files from an older build can't linger. It then re-signs the copy, since moving or modifying a bundle invalidates its signature. If macOS refuses to replace the app, quit the running copy first.

The build is ad-hoc signed, which is enough to run locally. macOS may still show a "cannot verify developer" prompt the first time if the app was moved between locations; right-click the app and choose **Open** once to approve it.

### How the icon is handled

`app_icon.PNG` is the single source of truth. `tools/make_icon.sh` converts it into a multi-resolution `HabitTracker.icns` at build time using macOS's built-in `sips` and `iconutil`. The generated `.icns` is a build artifact and is git-ignored — replace `app_icon.PNG` and re-run `make icon` (or just `make build`) to change the Dock icon.

## Where your data lives

```
~/Library/Application Support/HabitTracker/data.json
```

This location is used whether you run from source or from the bundled app, so switching between the two keeps your progress.

Writes are atomic (temp file + `os.replace`), so an interrupted save can never corrupt your data. If the file is ever unreadable, the app preserves a copy as `data.json.corrupt` and starts fresh rather than failing to launch.

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `←` / `→` | Previous / next month |
| `T` | Jump to today |

## Project layout

```
main.py                     entry point
habit_tracker/
  app.py                    calendar grid UI
  models.py                 habits, toggles, streaks
  storage.py                atomic JSON persistence
setup.py                    py2app configuration
tools/make_icon.sh          app_icon.PNG -> HabitTracker.icns
Makefile                    setup / run / icon / build / install / clean
```

## Notes

- Day cells in the future, or before a habit was created, are dimmed and not clickable.
- Toggling a day saves after a short debounce rather than on every click.
- The window auto-sizes so a full 31-day month is never squeezed.