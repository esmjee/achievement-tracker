import threading
import time
import tkinter as tk
from collections import defaultdict
from typing import Optional

from achievement_browser import AchievementBrowser
from steam_client import SteamAPIError, SteamClient
from tracker_store import PinEntry, TrackerConfig

DEFAULT_BACKGROUND_COLOR: str = "#1b1f27"
DEFAULT_OPACITY: float = 0.92
FOREGROUND_COLOR: str = "#ffffff"
MUTED_COLOR: str = "#7a8699"
FAINT_COLOR: str = "#565f6e"
ACCENT_COLOR: str = "#9fb4d1"
GOOD_COLOR: str = "#7fd67f"
BAD_COLOR: str = "#e06666"

RowKey = tuple[str, int, str]
RowUpdate = tuple[str, str]


class TrackerWidget:
    def __init__(self, root_window: tk.Tk, config: TrackerConfig) -> None:
        self.root_window: tk.Tk = root_window
        self.config: TrackerConfig = config
        self.steam_client: SteamClient = SteamClient(config["api_key"], config["steam_id64"])
        self.poll_seconds: int = config.get("poll_seconds", 60)
        self.drag_start_position: dict[str, int] = {"x": 0, "y": 0}
        self.achievement_browser: Optional[AchievementBrowser] = None
        self.row_status_labels: dict[RowKey, tk.Label] = {}
        self.background_color: str = config.get("bg_color", DEFAULT_BACKGROUND_COLOR)
        self.opacity: float = config.get("opacity", DEFAULT_OPACITY)
        self.static_background_widgets: list[tk.Widget] = []

        root_window.overrideredirect(True)
        root_window.attributes("-topmost", True)
        root_window.configure(bg=self.background_color)
        root_window.attributes("-alpha", self.opacity)

        self.context_menu: tk.Menu = tk.Menu(root_window, tearoff=0)
        self.context_menu.add_command(label="Refresh now", command=self.manual_refresh)
        self.context_menu.add_command(label="Manage achievements...", command=self.open_browser)
        self.context_menu.add_command(label="Appearance...", command=self.open_appearance)
        self.context_menu.add_command(label="Edit Steam credentials...", command=self.open_credentials)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Quit", command=root_window.destroy)

        self.main_frame: tk.Frame = tk.Frame(root_window, bg=self.background_color)
        self.main_frame.pack(fill="both", expand=True)
        self.make_draggable(self.main_frame)
        self.static_background_widgets.append(self.main_frame)

        self.top_bar: tk.Frame = tk.Frame(self.main_frame, bg=self.background_color)
        self.top_bar.pack(fill="x")
        self.make_draggable(self.top_bar)
        self.static_background_widgets.append(self.top_bar)
        title_label: tk.Label = tk.Label(
            self.top_bar, text="Achievement Tracker", fg=ACCENT_COLOR, bg=self.background_color,
            font=("Segoe UI", 9, "bold"),
        )
        title_label.pack(side="left", padx=8, pady=(6, 0))
        self.make_draggable(title_label)
        self.static_background_widgets.append(title_label)
        close_button: tk.Label = tk.Label(
            self.top_bar, text="✕", fg=ACCENT_COLOR, bg=self.background_color, font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        close_button.pack(side="right", padx=8, pady=(6, 0))
        close_button.bind("<Button-1>", lambda event: self.root_window.destroy())
        self.static_background_widgets.append(close_button)

        self.rows_frame: tk.Frame = tk.Frame(self.main_frame, bg=self.background_color)
        self.rows_frame.pack(fill="both", expand=True, padx=8, pady=(4, 0))
        self.make_draggable(self.rows_frame)
        self.static_background_widgets.append(self.rows_frame)

        self.countdown_label: tk.Label = tk.Label(
            self.main_frame, text="", fg=FAINT_COLOR, bg=self.background_color, font=("Segoe UI", 8)
        )
        self.countdown_label.pack(pady=(2, 6))
        self.make_draggable(self.countdown_label)
        self.static_background_widgets.append(self.countdown_label)

        window_x: int = config.get("window_x", 20)
        window_y: int = config.get("window_y", 40)
        root_window.geometry(f"+{window_x}+{window_y}")

        self.seconds_remaining: int = self.poll_seconds
        self.last_updated_timestamp: Optional[str] = None
        self.rebuild_rows()
        self.refresh_now()
        self.tick_countdown()

    def make_draggable(self, widget: tk.Widget, pinned_item: Optional[PinEntry] = None) -> None:
        widget.bind("<Button-1>", self.start_drag)
        widget.bind("<B1-Motion>", self.do_drag)
        widget.bind("<ButtonRelease-1>", self.end_drag)
        if pinned_item is None:
            widget.bind("<Button-3>", self.show_menu)
        else:
            widget.bind("<Button-3>", lambda event, pinned_item=pinned_item: self.show_row_menu(event, pinned_item))

    def show_menu(self, event: tk.Event) -> None:
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def show_row_menu(self, event: tk.Event, pinned_item: PinEntry) -> None:
        row_menu: tk.Menu = tk.Menu(self.root_window, tearoff=0)
        row_menu.add_command(
            label=f"Remove '{pinned_item['display_name']}'",
            command=lambda: self.remove_pinned_item(pinned_item),
        )
        row_menu.add_separator()
        row_menu.add_command(label="Refresh now", command=self.manual_refresh)
        row_menu.add_command(label="Manage achievements...", command=self.open_browser)
        row_menu.add_command(label="Appearance...", command=self.open_appearance)
        row_menu.add_command(label="Edit Steam credentials...", command=self.open_credentials)
        row_menu.add_separator()
        row_menu.add_command(label="Quit", command=self.root_window.destroy)
        row_menu.tk_popup(event.x_root, event.y_root)

    def remove_pinned_item(self, pinned_item: PinEntry) -> None:
        if pinned_item["type"] == "achievement":
            self.config.unpin_achievement(pinned_item["app_id"], pinned_item["api_name"])
        else:
            self.config.unpin_stat_goal(pinned_item["app_id"], pinned_item["stat_name"])
        self.config.save()
        self.rebuild_rows()
        self.refresh_now()

    def start_drag(self, event: tk.Event) -> None:
        self.drag_start_position["x"] = event.x
        self.drag_start_position["y"] = event.y

    def do_drag(self, event: tk.Event) -> None:
        new_x: int = self.root_window.winfo_x() + (event.x - self.drag_start_position["x"])
        new_y: int = self.root_window.winfo_y() + (event.y - self.drag_start_position["y"])
        self.root_window.geometry(f"+{new_x}+{new_y}")

    def end_drag(self, event: tk.Event) -> None:
        self.config["window_x"] = self.root_window.winfo_x()
        self.config["window_y"] = self.root_window.winfo_y()
        self.config.save()

    @staticmethod
    def row_key(pinned_item: PinEntry) -> RowKey:
        if pinned_item["type"] == "achievement":
            return ("achievement", pinned_item["app_id"], pinned_item["api_name"])
        return ("stat_goal", pinned_item["app_id"], pinned_item["stat_name"])

    def visible_pinned_items(self) -> list[PinEntry]:
        last_selected_app_id = self.config.get("last_selected_app_id")
        if last_selected_app_id is None:
            return self.config["pinned"]
        return [pinned_item for pinned_item in self.config["pinned"] if pinned_item["app_id"] == last_selected_app_id]

    def rebuild_rows(self) -> None:
        for child_widget in self.rows_frame.winfo_children():
            child_widget.destroy()
        self.row_status_labels = {}

        pinned_items = self.visible_pinned_items()
        if not pinned_items:
            placeholder_text = (
                "No achievements pinned.\nRight-click -> Manage achievements."
                if not self.config["pinned"]
                else "No pinned achievements for the last selected game."
            )
            placeholder_label: tk.Label = tk.Label(
                self.rows_frame, text=placeholder_text,
                fg=MUTED_COLOR, bg=self.background_color, font=("Segoe UI", 8), justify="left",
            )
            placeholder_label.pack(anchor="w", pady=4)
            self.make_draggable(placeholder_label)
            self.root_window.after_idle(lambda: self.root_window.geometry(""))
            return

        for pinned_item in pinned_items:
            row_frame: tk.Frame = tk.Frame(self.rows_frame, bg=self.background_color)
            row_frame.pack(fill="x", pady=2)
            self.make_draggable(row_frame, pinned_item=pinned_item)

            name_label: tk.Label = tk.Label(
                row_frame, text=pinned_item["display_name"], fg=FOREGROUND_COLOR, bg=self.background_color,
                font=("Segoe UI", 9, "bold"), anchor="w",
            )
            name_label.pack(anchor="w", fill="x")
            self.make_draggable(name_label, pinned_item=pinned_item)

            status_label: tk.Label = tk.Label(
                row_frame, text="Loading...", fg=MUTED_COLOR, bg=self.background_color, font=("Segoe UI", 8), anchor="w",
            )
            status_label.pack(anchor="w", fill="x")
            self.make_draggable(status_label, pinned_item=pinned_item)

            self.row_status_labels[self.row_key(pinned_item)] = status_label

        self.root_window.after_idle(lambda: self.root_window.geometry(""))

    def open_browser(self) -> None:
        if self.achievement_browser is not None and self.achievement_browser.winfo_exists():
            self.achievement_browser.lift()
            return
        self.achievement_browser = AchievementBrowser(self.root_window, self.config, on_change=self.on_pinned_items_changed)

    def open_credentials(self) -> None:
        from setup_dialog import SetupDialog

        def on_credentials_saved() -> None:
            self.steam_client = SteamClient(self.config["api_key"], self.config["steam_id64"])
            self.manual_refresh()

        SetupDialog(self.root_window, self.config, on_credentials_saved)

    def open_appearance(self) -> None:
        from settings_dialog import AppearanceDialog
        AppearanceDialog(self.root_window, self.background_color, self.opacity, self.apply_appearance)

    def apply_appearance(self, background_color: str, opacity: float) -> None:
        self.background_color = background_color
        self.opacity = opacity
        self.config["bg_color"] = background_color
        self.config["opacity"] = opacity
        self.config.save()

        self.root_window.configure(bg=background_color)
        self.root_window.attributes("-alpha", opacity)
        for widget in self.static_background_widgets:
            widget.config(bg=background_color)
        for row_frame in self.rows_frame.winfo_children():
            row_frame.config(bg=background_color)
            for child_widget in row_frame.winfo_children():
                child_widget.config(bg=background_color)

    def on_pinned_items_changed(self) -> None:
        self.rebuild_rows()
        self.refresh_now()

    def refresh_now(self) -> None:
        threading.Thread(target=self.poll_all, daemon=True).start()

    def manual_refresh(self) -> None:
        self.seconds_remaining = self.poll_seconds
        self.refresh_now()

    def tick_countdown(self) -> None:
        status_text: str = f"updated {self.last_updated_timestamp}" if self.last_updated_timestamp else "not updated yet"
        self.countdown_label.config(text=f"{status_text} · next check in {self.seconds_remaining}s")
        if self.seconds_remaining <= 0:
            self.seconds_remaining = self.poll_seconds
            self.refresh_now()
        else:
            self.seconds_remaining -= 1
        self.root_window.after(1000, self.tick_countdown)

    def poll_all(self) -> None:
        pinned_items_by_app_id: dict[int, list[PinEntry]] = defaultdict(list)
        for pinned_item in self.visible_pinned_items():
            pinned_items_by_app_id[pinned_item["app_id"]].append(pinned_item)

        row_updates: dict[RowKey, RowUpdate] = {}
        for app_id, pinned_items in pinned_items_by_app_id.items():
            needs_achievements: bool = any(pinned_item["type"] == "achievement" for pinned_item in pinned_items)
            needs_stats: bool = any(
                pinned_item["type"] == "stat_goal"
                or (pinned_item["type"] == "achievement" and pinned_item.get("stat_name"))
                for pinned_item in pinned_items
            )
            achievement_states: dict[str, dict] = {}
            stat_values: dict[str, int] = {}
            error_message: Optional[str] = None
            try:
                if needs_achievements:
                    achievement_states = self.steam_client.get_player_achievements(app_id)
                if needs_stats:
                    stat_values = self.steam_client.get_user_stats(app_id)
            except SteamAPIError as error:
                error_message = str(error)

            for pinned_item in pinned_items:
                key: RowKey = self.row_key(pinned_item)
                if error_message:
                    row_updates[key] = (error_message[:44], BAD_COLOR)
                elif pinned_item["type"] == "achievement":
                    achievement_state = achievement_states.get(pinned_item["api_name"], {})
                    if achievement_state.get("achieved"):
                        row_updates[key] = ("Unlocked ✓", GOOD_COLOR)
                    elif pinned_item.get("stat_name"):
                        current_value = stat_values.get(pinned_item["stat_name"], 0)
                        target_value = pinned_item["target"]
                        if current_value >= target_value:
                            row_updates[key] = (f"Unlocked ✓ ({current_value:,}/{target_value:,})", GOOD_COLOR)
                        else:
                            row_updates[key] = (f"{current_value:,} / {target_value:,}", FOREGROUND_COLOR)
                    else:
                        row_updates[key] = ("Locked", MUTED_COLOR)
                else:
                    current_value = stat_values.get(pinned_item["stat_name"], 0)
                    target_value = pinned_item["target"]
                    if current_value >= target_value:
                        row_updates[key] = (f"Unlocked ✓ ({current_value:,}/{target_value:,})", GOOD_COLOR)
                    else:
                        row_updates[key] = (f"{current_value:,} / {target_value:,}", FOREGROUND_COLOR)

        self.root_window.after(0, self.apply_updates, row_updates)

    def apply_updates(self, row_updates: dict[RowKey, RowUpdate]) -> None:
        self.last_updated_timestamp = time.strftime("%H:%M:%S")
        for key, status_label in self.row_status_labels.items():
            if key in row_updates:
                status_text, status_color = row_updates[key]
                status_label.config(text=status_text, fg=status_color)
