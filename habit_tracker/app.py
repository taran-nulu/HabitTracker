"""The main application window: a month-view grid of habits x days."""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date

import customtkinter as ctk
from tkinter import messagebox

from .models import Store

# Layout metrics (pixels, before CustomTkinter's scaling is applied).
DAY_CELL_W = 30
DAY_CELL_H = 26
HEADER_H = 20
HABIT_COL_W = 210

# Fixed chrome inside the habit column: colour dot, gaps, streak badge, Edit.
NAME_CHROME_W = 12 + 2 + 8 + 42 + 4 + 44 + 4

# Horizontal padding around each day cell. Must be identical for the header
# labels and the day buttons, or the columns drift apart across the month.
DAY_PAD = 1

# Scroll-frame and window chrome that sit outside the grid itself. Measured
# from a live window: 16px scrollbar + 2x14px rounded frame + 2x18px window pad.
GRID_PADDING = 16 + 2 * 14
WINDOW_PADDING_X = 2 * 18

# Colours are (light_mode, dark_mode) tuples so CustomTkinter switches them
# automatically when the appearance mode changes.
C_BG = ("#f2f3f5", "#1c1e22")
C_CARD = ("#ffffff", "#25282d")
C_CARD_HOVER = ("#e8eaee", "#2f333a")
C_TEXT = ("#16181c", "#e7e9ec")
C_MUTED = ("#6c7280", "#8d949f")
C_CELL_EMPTY = ("#ffffff", "#2b2e34")
C_CELL_HOVER = ("#dfe3e9", "#3a3f48")
C_CELL_FUTURE = ("#f7f8fa", "#212429")
C_TODAY_RING = ("#4c8dff", "#4c8dff")


class HabitApp(ctk.CTk):
    """Calendar-grid habit tracker."""

    def __init__(self) -> None:
        super().__init__()

        self.store = Store()
        self.store.load()

        self.title("Habit Tracker")
        # Wide enough that a full 31-day month is never squeezed: habit column
        # + 31 day columns + window/scroll padding. Resized on first draw once
        # the real column widths are known.
        self.geometry("1340x700")
        self.minsize(980, 440)

        today = date.today()
        self.view_year = today.year
        self.view_month = today.month

        self._save_job: str | None = None
        self._habit_col_w = HABIT_COL_W
        self._day_col_w = DAY_CELL_W
        self._day_buttons: dict[tuple[str, str], ctk.CTkButton] = {}
        self._streak_labels: dict[str, ctk.CTkLabel] = {}
        self._habit_menus: dict[str, tk.Menu] = {}

        self._configure_layout()
        self._build_header()
        self._build_grid_area()

        self.refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Left>", lambda _e: self.shift_month(-1))
        self.bind("<Right>", lambda _e: self.shift_month(1))
        self.bind("<t>", lambda _e: self.go_to_today())

    # ------------------------------------------------------------- layout

    def _configure_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Habit Tracker",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=C_TEXT,
        ).grid(row=0, column=0, sticky="w")

        self.add_button = ctk.CTkButton(
            header,
            text="+  Add Habit",
            width=130,
            height=36,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.add_habit,
        )
        self.add_button.grid(row=0, column=1, padx=(10, 0))

        self.theme_button = ctk.CTkButton(
            header,
            text="Light" if ctk.get_appearance_mode() == "Dark" else "Dark",
            width=78,
            height=36,
            corner_radius=10,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            text_color=C_MUTED,
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=0, column=2, padx=(8, 0))

        # --- month navigation row ---
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=18, pady=(10, 10))
        nav.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            nav,
            text="<",
            width=38,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            text_color=C_MUTED,
            font=ctk.CTkFont(size=17, weight="bold"),
            command=lambda: self.shift_month(-1),
        ).grid(row=0, column=0)

        self.month_label = ctk.CTkLabel(
            nav,
            text="",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=C_TEXT,
        )
        self.month_label.grid(row=0, column=1, sticky="w", padx=14)

        ctk.CTkButton(
            nav,
            text=">",
            width=38,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            text_color=C_MUTED,
            font=ctk.CTkFont(size=17, weight="bold"),
            command=lambda: self.shift_month(1),
        ).grid(row=0, column=2)

        ctk.CTkButton(
            nav,
            text="Today",
            width=74,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            text_color=C_MUTED,
            font=ctk.CTkFont(size=14),
            command=self.go_to_today,
        ).grid(row=0, column=3, padx=(10, 0))

        self.summary_label = ctk.CTkLabel(
            nav,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=C_MUTED,
        )
        self.summary_label.grid(row=0, column=4, padx=(16, 0), sticky="e")

    def _build_grid_area(self) -> None:
        self.grid_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=C_CARD,
            corner_radius=14,
            scrollbar_button_color=C_MUTED,
            scrollbar_button_hover_color=C_TEXT,
        )
        self.grid_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))

    # ------------------------------------------------------------- render

    def _measure_habit_col(self) -> int:
        """Width of the habit column: wide enough for the longest name.

        Measuring the text (rather than hardcoding a width) keeps the header
        and every row aligned, so day cells sit directly under their day
        numbers no matter how long a habit name is.
        """
        widest = 0
        font = ctk.CTkFont(size=14, weight="bold")
        try:
            for habit in self.store.habits:
                widest = max(widest, font.measure(habit.name))
        except tk.TclError:
            widest = 0
        return max(HABIT_COL_W, widest + NAME_CHROME_W + 12)

    def refresh(self) -> None:
        """Rebuild the whole grid from the store.

        Everything is placed in a single grid on ``self.grid_frame`` so that
        every day cell shares its column with the corresponding day number.
        Separate frames per row would each resolve their own column widths and
        drift apart across a 31-day month.
        """
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self._day_buttons.clear()
        self._streak_labels.clear()
        self._habit_menus.clear()

        self.month_label.configure(
            text=f"{calendar.month_name[self.view_month]} {self.view_year}"
        )

        days_in_month = calendar.monthrange(self.view_year, self.view_month)[1]
        today = date.today()
        self._habit_col_w = self._measure_habit_col()
        self._day_col_w = self._measure_day_col(days_in_month)

        # Column 0 is the habit column; day columns follow; last column absorbs
        # whatever width is left over.
        self.grid_frame.grid_columnconfigure(0, minsize=self._habit_col_w, weight=0)
        for i in range(1, days_in_month + 1):
            self.grid_frame.grid_columnconfigure(
                i, minsize=self._day_col_w + DAY_PAD * 2, weight=0
            )
        self.grid_frame.grid_columnconfigure(days_in_month + 1, weight=1)

        self._build_header_row(days_in_month, today)

        # Now that the real column widths are known, make sure the window is
        # wide enough to show the month without squeezing it.
        self.update_idletasks()
        needed = (
            self._habit_col_w
            + days_in_month * (self._day_col_w + DAY_PAD * 2)
            + 2 * GRID_PADDING + WINDOW_PADDING_X
        )
        if self.winfo_width() < needed:
            self.geometry(f"{int(needed)}x{self.winfo_height()}")

        if not self.store.habits:
            self._build_empty_state(days_in_month)
        else:
            for index, habit in enumerate(self.store.habits):
                self._build_habit_row(habit, index, days_in_month, today)

        self._update_summary(today)

    def _measure_day_col(self, days: int) -> int:
        """Width for a day column, wide enough for the widest day number.

        A two-digit label ("30") needs more room than a one-digit one ("1").
        Grid sizes a column to its largest child, so a column sized only to
        "30" would stay correct while every other column stayed at its minimum
        — leaving that one cell out of line with its header. Measuring the
        real widget requirement (not just the glyphs) keeps all day columns
        exactly equal.

        This creates and immediately destroys a throwaway probe label, so the
        measurement reflects CustomTkinter's own padding and DPI scaling.
        """
        probes = [
            ctk.CTkLabel(
                self.grid_frame,
                text=str(day),
                width=DAY_CELL_W,
                height=DAY_CELL_H,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight=style),
            )
            for day in range(1, days + 1)  # every day number, to catch outliers
            for style in ("normal", "bold")  # today's number is bold
        ]
        widest = DAY_CELL_W
        try:
            # winfo_reqwidth is only meaningful once Tk has computed geometry.
            self.update_idletasks()
            for probe in probes:
                widest = max(widest, probe.winfo_reqwidth())
        except tk.TclError:
            widest = DAY_CELL_W
        finally:
            for probe in probes:
                probe.destroy()

        return widest

    def _build_header_row(self, days: int, today: date) -> None:
        ctk.CTkLabel(
            self.grid_frame,
            text="Habit",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C_MUTED,
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(4, 0))

        for day in range(1, days + 1):
            day_date = date(self.view_year, self.view_month, day)
            is_today = day_date == today

            ctk.CTkLabel(
                self.grid_frame,
                text=calendar.day_abbr[day_date.weekday()][0],
                width=self._day_col_w,
                height=HEADER_H,
                text_color=C_MUTED,
                font=ctk.CTkFont(size=10),
            ).grid(row=0, column=day, padx=DAY_PAD)

            ctk.CTkLabel(
                self.grid_frame,
                text=str(day),
                width=self._day_col_w,
                height=DAY_CELL_H,
                corner_radius=8,
                text_color=C_TEXT if is_today else C_MUTED,
                fg_color=C_TODAY_RING if is_today else "transparent",
                font=ctk.CTkFont(size=12, weight="bold" if is_today else "normal"),
            ).grid(row=1, column=day, padx=DAY_PAD, pady=(2, 6))

    def _build_empty_state(self, days_in_month: int) -> None:
        box = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        box.grid(row=2, column=0, columnspan=days_in_month + 2, pady=90)

        ctk.CTkLabel(
            box,
            text="No habits yet",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C_TEXT,
        ).pack()
        ctk.CTkLabel(
            box,
            text="Add your first habit and start checking off days.",
            font=ctk.CTkFont(size=14),
            text_color=C_MUTED,
        ).pack(pady=(6, 18))
        ctk.CTkButton(
            box,
            text="+  Add Habit",
            width=150,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.add_habit,
        ).pack()

    def _build_habit_row(
        self, habit, index: int, days_in_month: int, today: date
    ) -> None:
        row = index + 2  # rows 0-1 are the weekday/day-number header
        parent = self.grid_frame

        # --- name cell ---
        name_cell = ctk.CTkFrame(parent, fg_color="transparent")
        name_cell.grid(row=row, column=0, sticky="w")

        dot = ctk.CTkLabel(
            name_cell,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color=habit.color,
        )
        dot.grid(row=0, column=0, padx=(2, 0), pady=4)

        name_label = ctk.CTkLabel(
            name_cell,
            text=habit.name,
            anchor="w",
            width=self._habit_col_w - NAME_CHROME_W,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C_TEXT,
        )
        name_label.grid(row=0, column=1, padx=(8, 0), sticky="w")

        # --- streak badge ---
        streak = self.store.current_streak(habit.id)
        streak_label = ctk.CTkLabel(
            name_cell,
            text=f"{streak}d" if streak else "-",
            width=42,
            height=22,
            corner_radius=11,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ffffff" if streak else C_MUTED,
            fg_color=habit.color if streak else "transparent",
        )
        streak_label.grid(row=0, column=2, padx=(4, 0))
        self._streak_labels[habit.id] = streak_label

        menu = self._build_habit_menu(habit)
        ctk.CTkButton(
            name_cell,
            text="Edit",
            width=44,
            height=24,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=C_MUTED,
            command=lambda h=habit, m=menu: m.post(
                self.winfo_pointerx(), self.winfo_pointery()
            ),
        ).grid(row=0, column=3, padx=(4, 0))

        name_cell.bind("<Button-3>", lambda e, m=menu: m.post(e.x_root, e.y_root))

        # --- day cells ---
        for day in range(1, days_in_month + 1):
            day_date = date(self.view_year, self.view_month, day)
            self._build_day_cell(parent, row, habit, day_date, day, today)

    def _build_day_cell(
        self, parent, row: int, habit, day_date: date, day: int, today: date
    ) -> None:
        done = self.store.is_done(habit.id, day_date)
        is_future = day_date > today
        before_creation = day_date < habit.created

        if done:
            fg, hover = habit.color, _lighten(habit.color, 0.12)
        elif is_future or before_creation:
            fg, hover = C_CELL_FUTURE, C_CELL_FUTURE
        elif day_date == today:
            fg, hover = C_CELL_HOVER, C_CARD_HOVER
        else:
            fg, hover = C_CELL_EMPTY, C_CELL_HOVER

        button = ctk.CTkButton(
            parent,
            text="",
            width=self._day_col_w,
            height=DAY_CELL_H,
            corner_radius=7,
            fg_color=fg,
            hover_color=hover,
            border_width=0,
            command=None if (is_future or before_creation)
            else lambda h=habit, d=day_date: self._toggle_cell(h, d),
        )
        button.grid(row=row, column=day, padx=DAY_PAD, pady=2)
        self._day_buttons[(habit.id, day_date.isoformat())] = button

    # --------------------------------------------------------- behaviour

    def _toggle_cell(self, habit, day_date: date) -> None:
        done = self.store.toggle(habit.id, day_date)
        button = self._day_buttons.get((habit.id, day_date.isoformat()))
        if button is not None:
            if done:
                button.configure(fg_color=habit.color, hover_color=_lighten(habit.color, 0.12))
            else:
                button.configure(fg_color=C_CELL_EMPTY, hover_color=C_CELL_HOVER)

        self._refresh_streak(habit)
        self._update_summary(date.today())
        self._schedule_save()

    def _refresh_streak(self, habit) -> None:
        label = self._streak_labels.get(habit.id)
        if label is None:
            return
        streak = self.store.current_streak(habit.id)
        if streak:
            label.configure(text=f"{streak}d", fg_color=habit.color, text_color="#ffffff")
        else:
            label.configure(text="-", fg_color="transparent", text_color=C_MUTED)

    def _update_summary(self, today: date) -> None:
        if not self.store.habits:
            self.summary_label.configure(text="")
            return
        done = sum(1 for h in self.store.habits if self.store.is_done(h.id, today))
        total = len(self.store.habits)
        self.summary_label.configure(text=f"{done} of {total} done today")

    def shift_month(self, delta: int) -> None:
        # Work in zero-based month indices so year rollover is a simple floor-div.
        index = self.view_month - 1 + delta
        self.view_year += index // 12
        self.view_month = index % 12 + 1
        self.refresh()

    def go_to_today(self) -> None:
        today = date.today()
        self.view_year, self.view_month = today.year, today.month
        self.refresh()

    def toggle_theme(self) -> None:
        new_mode = "light" if ctk.get_appearance_mode() == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        self.theme_button.configure(text="Light" if new_mode == "dark" else "Dark")
        self.refresh()

    # ---------------------------------------------------------- habits

    def add_habit(self) -> None:
        name = self._prompt("New Habit", "Habit name", "")
        if not name:
            return
        try:
            self.store.add_habit(name)
        except ValueError as exc:
            messagebox.showerror("Habit Tracker", str(exc), parent=self)
            return
        self.refresh()
        self._save()

    def _rename_habit(self, habit) -> None:
        name = self._prompt("Rename Habit", "Habit name", habit.name)
        if not name or name == habit.name:
            return
        try:
            self.store.rename_habit(habit.id, name)
        except ValueError as exc:
            messagebox.showerror("Habit Tracker", str(exc), parent=self)
            return
        self.refresh()
        self._save()

    def _delete_habit(self, habit) -> None:
        confirmed = messagebox.askyesno(
            "Delete habit",
            f"Delete \"{habit.name}\"?\n\nAll of its recorded days will be removed too. "
            "This cannot be undone.",
            parent=self,
        )
        if not confirmed:
            return
        self.store.delete_habit(habit.id)
        self.refresh()
        self._save()

    def _build_habit_menu(self, habit) -> tk.Menu:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Rename...", command=lambda: self._rename_habit(habit))
        menu.add_command(label="Delete...", command=lambda: self._delete_habit(habit))
        self._habit_menus[habit.id] = menu
        return menu

    # --------------------------------------------------------- dialogs

    def _prompt(self, title: str, message: str, initial: str) -> str | None:
        """Modal single-field prompt. Returns the text, or None if cancelled."""
        top = ctk.CTkToplevel(self)
        top.title(title)
        top.resizable(False, False)
        top.transient(self)

        result: list[str | None] = [None]

        panel = ctk.CTkFrame(top, fg_color="transparent")
        panel.pack(padx=22, pady=20)

        ctk.CTkLabel(
            panel,
            text=title,
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            panel,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=C_MUTED,
        ).pack(anchor="w", pady=(2, 12))

        entry = ctk.CTkEntry(
            panel,
            width=280,
            height=34,
            font=ctk.CTkFont(size=14),
        )
        entry.insert(0, initial)
        entry.select_range(0, "end")
        entry.pack()
        entry.focus_set()

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", pady=(16, 0))

        def accept() -> None:
            result[0] = entry.get().strip()
            top.destroy()

        def cancel() -> None:
            result[0] = None
            top.destroy()

        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=100,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            text_color=C_MUTED,
            command=cancel,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            buttons,
            text="Save",
            width=100,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=accept,
        ).pack(side="right")

        top.bind("<Return>", lambda _e: accept())
        top.bind("<Escape>", lambda _e: cancel())
        top.protocol("WM_DELETE_WINDOW", cancel)

        self.wait_window(top)
        return result[0]

    # ---------------------------------------------------------- saving

    def _schedule_save(self) -> None:
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
        self._save_job = self.after(400, self._save)

    def _save(self) -> None:
        self._save_job = None
        try:
            self.store.save()
        except OSError as exc:
            messagebox.showerror(
                "Habit Tracker", f"Could not save your progress:\n\n{exc}", parent=self
            )

    def _on_close(self) -> None:
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
            self._save_job = None
        self._save()
        self.destroy()


def _lighten(hex_color: str, amount: float) -> str:
    """Lighten a #rrggbb colour by `amount` (0-1). Used for hover states."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = HabitApp()
    app.mainloop()