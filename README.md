# Habit Tracker

A macOS desktop habit tracker built with [CustomTkinter](https://github.com/tomschneum/customtkinter), packaged with [py2app](https://py2app.readthedocs.io/).

Habits are laid out as a month calendar — one row per habit, one column per day — so you can see at a glance what you have and haven't done.

## Features

- Month grid with click-to-toggle day cells
- Add, edit and delete habits — one **Edit** dialog covers name and color (delete asks for confirmation)
- Per-habit color, picked from a palette of swatches or typed as any hex value
- Current streak and longest-ever streak per habit
- Previous / next month navigation and a `Today` jump
- Dark / light theme toggle
- Progress saved automatically and restored on launch
- Launches from the Dock as a normal macOS app

## Requirements

- macOS 11 or newer
- Python 3.9+ (developed against 3.13)

## Install

```bash
make install
```

Builds the app and installs it to `/Applications`, ready to launch and pin to the Dock. See [Install the app](#install-the-app) for details, and [Updating an existing install](#updating-an-existing-install) if you have already installed it once.

To run straight from source instead:

```bash
make setup     # creates .venv and installs dependencies
make run       # launches the app
```

## Install the app

```bash
make install
```

That is the whole command. It builds the app, replaces the copy in `/Applications`, and re-signs it. When it finishes, the app is ready to launch:

1. Open **Applications → Habit Tracker**.
2. Right-click its icon in the Dock and choose **Options → Keep in Dock** to pin it permanently.

If macOS shows a "cannot verify developer" prompt, right-click the app and choose **Open** once to approve it. The app is ad-hoc signed, so this only happens the first time.

If you only want the bundle without installing it, `make build` leaves it at `dist/Habit Tracker.app`.

## Updating an existing install

Run the same command again after changing anything:

```bash
make install
```

| You changed | Command |
| --- | --- |
| Python code (`habit_tracker/*.py`, `main.py`) | `make install` |
| `app_icon.PNG` (the Dock icon) | `make install` |
| `requirements.txt` | `make install` |
| `setup.py` (bundle name, version) | `make clean install` |

You never need to download anything — the app is built from this source tree on your Mac, so updating is just rebuilding.

Notes:

- **Quit the app before installing.** If it is running, macOS may refuse to replace it.
- `make install` deletes the existing app before copying, so files from an older build cannot linger, and your progress is never lost (it lives outside the bundle — see below).
- `make install` depends on `make build`, which in turn depends on `make setup` and `make icon`. Dependencies are reinstalled and the icon is regenerated on every build, automatically.
- While iterating on code, `make run` is much faster than a full rebuild — it launches straight from source and uses the same data file as the installed app.

To see what a target will do without running it, use `make -n install`.

### How the icon is handled

The `app_icon` file is the single source of truth. `tools/make_icon.sh` converts it into a multi-resolution `HabitTracker.icns` at build time using macOS's built-in `sips` and `iconutil`, then the bundle embeds that as its Dock icon.

The script accepts `app_icon.PNG`, `app_icon.png`, `app_icon.jpg`, `app_icon.jpeg`, or `app_icon` regardless of the file's real format, so replacing the icon with a differently-named or differently-encoded file works without touching any code. The generated `.icns` is a build artifact and is git-ignored — edit the source icon and re-run `make install`.

For the most native look, supply a square image **with a transparent background**. Icons without an alpha channel render as plain squares in the Dock.

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
- Each habit shows two badges: its current streak (`5d`) and its longest streak ever (`best 12d`). The current streak survives an unticked today, and only breaks once a whole day is missed.
- Habits are auto-assigned the least-used color from the palette. Use **Edit** on a habit row to change its name and color together — pick from the swatches or type any hex value such as `#4C8DFF`. **Delete** removes it.
- Toggling a day saves after a short debounce rather than on every click.
- The window auto-sizes so a full 31-day month is never squeezed.