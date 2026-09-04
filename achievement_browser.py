import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Optional

from stat_matcher import StatMatcher
from steam_client import SteamAPIError, SteamClient
from tracker_store import GameEntry, PinEntry, TrackerConfig

AchievementEntry = dict[str, Any]
StatEntry = dict[str, Any]


class AchievementBrowser(tk.Toplevel):
    def __init__(self, master: tk.Misc, config: TrackerConfig, on_change: Callable[[], None]) -> None:
        super().__init__(master)
        self.title("Manage Achievements")
        self.geometry("640x460")
        self.config_data: TrackerConfig = config
        self.steam_client: SteamClient = SteamClient(config["api_key"], config["steam_id64"])
        self.on_change: Callable[[], None] = on_change
        self.current_app_id: Optional[int] = None
        self.current_game_name: Optional[str] = None
        self.achievements: list[AchievementEntry] = []
        self.locked_achievements: list[AchievementEntry] = []
        self.stats: list[StatEntry] = []
        self.stat_values: dict[str, int] = {}

        self.build_widgets()
        self.refresh_games_list()

    def build_widgets(self) -> None:
        content_frame: ttk.Frame = ttk.Frame(self, padding=8)
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        left_panel: ttk.Frame = ttk.Frame(content_frame)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 8))

        ttk.Label(left_panel, text="Games").pack(anchor="w")
        self.games_listbox: tk.Listbox = tk.Listbox(left_panel, width=24, height=18, exportselection=False)
        self.games_listbox.pack(fill="y", expand=True)
        self.games_listbox.bind("<<ListboxSelect>>", self.on_select_game)

        ttk.Button(left_panel, text="Add from library...", command=self.open_library_picker).pack(fill="x", pady=(6, 0))
        ttk.Button(left_panel, text="Remove selected game", command=self.remove_selected_game).pack(fill="x", pady=(4, 0))

        right_panel: ttk.Frame = ttk.Frame(content_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.rowconfigure(2, weight=3)
        right_panel.rowconfigure(5, weight=1)
        right_panel.columnconfigure(0, weight=1)

        achievements_header: ttk.Frame = ttk.Frame(right_panel)
        achievements_header.grid(row=0, column=0, sticky="ew")
        achievements_header.columnconfigure(0, weight=1)
        ttk.Label(achievements_header, text="Locked achievements (double-click to pin/unpin)").grid(row=0, column=0, sticky="w")
        self.achievements_progress_label: ttk.Label = ttk.Label(achievements_header, text="")
        self.achievements_progress_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.achievements_progress_bar: ttk.Progressbar = ttk.Progressbar(achievements_header, orient="horizontal", mode="determinate")
        self.achievements_progress_bar.grid(row=2, column=0, sticky="ew", pady=(2, 0))

        self.achievements_search_variable: tk.StringVar = tk.StringVar()
        self.achievements_search_variable.trace_add("write", lambda *_: self.apply_achievements_filter())
        search_row: ttk.Frame = ttk.Frame(right_panel)
        search_row.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Search:").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(search_row, textvariable=self.achievements_search_variable).grid(row=0, column=1, sticky="ew")

        achievements_frame: ttk.Frame = ttk.Frame(right_panel)
        achievements_frame.grid(row=2, column=0, sticky="nsew")
        achievements_frame.rowconfigure(0, weight=1)
        achievements_frame.columnconfigure(0, weight=1)
        self.achievements_tree: ttk.Treeview = ttk.Treeview(
            achievements_frame, columns=("pinned", "name", "description", "stat", "current", "target"), show="headings", height=10
        )
        self.achievements_tree.heading("pinned", text="Pinned")
        self.achievements_tree.heading("name", text="Achievement")
        self.achievements_tree.heading("description", text="Description")
        self.achievements_tree.heading("stat", text="Linked Stat")
        self.achievements_tree.heading("current", text="Current")
        self.achievements_tree.heading("target", text="Target")
        self.achievements_tree.column("pinned", width=60, anchor="center", stretch=False)
        self.achievements_tree.column("name", width=160, anchor="w")
        self.achievements_tree.column("description", width=220, anchor="w")
        self.achievements_tree.column("stat", width=140, anchor="w", stretch=False)
        self.achievements_tree.column("current", width=90, anchor="center", stretch=False)
        self.achievements_tree.column("target", width=90, anchor="center", stretch=False)
        self.achievements_tree.grid(row=0, column=0, sticky="nsew")
        self.achievements_tree.bind("<Double-1>", self.toggle_pin_achievement)
        achievements_scrollbar: ttk.Scrollbar = ttk.Scrollbar(achievements_frame, orient="vertical", command=self.achievements_tree.yview)
        achievements_scrollbar.grid(row=0, column=1, sticky="ns")
        self.achievements_tree.config(yscrollcommand=achievements_scrollbar.set)

        ttk.Label(right_panel, text="Stats (double-click to pin/unpin as a progress goal)").grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.stats_search_variable: tk.StringVar = tk.StringVar()
        self.stats_search_variable.trace_add("write", lambda *_: self.apply_stats_filter())
        stats_search_row: ttk.Frame = ttk.Frame(right_panel)
        stats_search_row.grid(row=4, column=0, sticky="ew", pady=(2, 4))
        stats_search_row.columnconfigure(1, weight=1)
        ttk.Label(stats_search_row, text="Search:").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(stats_search_row, textvariable=self.stats_search_variable).grid(row=0, column=1, sticky="ew")

        self.stats_tree: ttk.Treeview = ttk.Treeview(
            right_panel, columns=("pinned", "name", "current", "target"), show="headings", height=6
        )
        self.stats_tree.heading("pinned", text="Pinned")
        self.stats_tree.heading("name", text="Stat")
        self.stats_tree.heading("current", text="Current")
        self.stats_tree.heading("target", text="Target")
        self.stats_tree.column("pinned", width=60, anchor="center", stretch=False)
        self.stats_tree.column("name", anchor="w")
        self.stats_tree.column("current", width=100, anchor="center", stretch=False)
        self.stats_tree.column("target", width=100, anchor="center", stretch=False)
        self.stats_tree.grid(row=5, column=0, sticky="nsew")
        self.stats_tree.bind("<Double-1>", self.toggle_pin_stat)

        self.status_label: ttk.Label = ttk.Label(self, text="", foreground="#a33")
        self.status_label.pack(fill="x", padx=8)

    def set_status(self, text: str) -> None:
        self.status_label.config(text=text)

    def refresh_games_list(self) -> None:
        self.games_listbox.delete(0, tk.END)
        for game_entry in self.config_data.games:
            self.games_listbox.insert(tk.END, f"{game_entry['name']} ({game_entry['app_id']})")

    def open_library_picker(self) -> None:
        already_added_app_ids: set[int] = {game_entry["app_id"] for game_entry in self.config_data.games}
        GameLibraryPicker(self, self.steam_client, already_added_app_ids, self.on_games_picked)

    def on_games_picked(self, picked_games: list[GameEntry]) -> None:
        for game_entry in picked_games:
            self.config_data.add_game(game_entry["app_id"], game_entry["name"])
        self.config_data.save()
        self.refresh_games_list()
        self.on_change()

    def remove_selected_game(self) -> None:
        selection: tuple[int, ...] = self.games_listbox.curselection()
        if not selection:
            return
        game_entry: GameEntry = self.config_data.games[selection[0]]
        if not messagebox.askyesno("Remove game", f"Remove {game_entry['name']} and unpin everything from it?"):
            return
        self.config_data.remove_game(game_entry["app_id"])
        if self.config_data.get("last_selected_app_id") == game_entry["app_id"]:
            self.config_data["last_selected_app_id"] = None
        self.config_data.save()
        self.current_app_id = None
        self.locked_achievements = []
        self.achievements_tree.delete(*self.achievements_tree.get_children())
        self.stats_tree.delete(*self.stats_tree.get_children())
        self.achievements_progress_label.config(text="")
        self.achievements_progress_bar.config(value=0, maximum=1)
        self.refresh_games_list()
        self.on_change()

    def on_select_game(self, event: tk.Event) -> None:
        selection: tuple[int, ...] = self.games_listbox.curselection()
        if not selection:
            return
        game_entry: GameEntry = self.config_data.games[selection[0]]
        self.current_app_id = game_entry["app_id"]
        self.current_game_name = game_entry["name"]
        self.config_data["last_selected_app_id"] = game_entry["app_id"]
        self.config_data.save()
        self.on_change()
        self.set_status("Loading achievements...")
        self.achievements_tree.delete(*self.achievements_tree.get_children())
        self.stats_tree.delete(*self.stats_tree.get_children())

        def load_game_data() -> None:
            try:
                schema = self.steam_client.get_schema(self.current_app_id)
                progress = self.steam_client.get_player_achievements(self.current_app_id)
                stat_values = self.steam_client.get_user_stats(self.current_app_id)
            except SteamAPIError as error:
                self.after(0, self.set_status, str(error))
                return
            self.after(0, self.populate_game, schema, progress, stat_values)

        threading.Thread(target=load_game_data, daemon=True).start()

    def populate_game(
        self,
        schema: dict[str, Any],
        progress: dict[str, dict[str, Any]],
        stat_values: dict[str, int],
    ) -> None:
        self.set_status("")
        self.achievements = schema["achievements"]
        self.stats = schema["stats"]
        self.stat_values = stat_values

        unlocked_count: int = sum(
            1 for achievement_entry in self.achievements
            if progress.get(achievement_entry["api_name"], {}).get("achieved")
        )
        total_count: int = len(self.achievements)
        self.achievements_progress_bar.config(maximum=max(total_count, 1), value=unlocked_count)
        unlocked_percent: int = round(100 * unlocked_count / total_count) if total_count else 0
        self.achievements_progress_label.config(text=f"{unlocked_count} / {total_count} unlocked ({unlocked_percent}%)")

        self.locked_achievements = [
            achievement_entry for achievement_entry in self.achievements
            if not progress.get(achievement_entry["api_name"], {}).get("achieved")
        ]
        self.achievements_search_variable.set("")
        self.stats_search_variable.set("")

    def apply_achievements_filter(self) -> None:
        search_text: str = self.achievements_search_variable.get().strip().lower()
        self.achievements_tree.delete(*self.achievements_tree.get_children())
        for achievement_entry in self.locked_achievements:
            searchable_text: str = f"{achievement_entry['display_name']} {achievement_entry['description']}".lower()
            if search_text in searchable_text:
                self.insert_achievement_row(achievement_entry)

    def apply_stats_filter(self) -> None:
        search_text: str = self.stats_search_variable.get().strip().lower()
        self.stats_tree.delete(*self.stats_tree.get_children())
        for stat_entry in self.stats:
            if search_text in stat_entry["display_name"].lower():
                self.insert_stat_row(stat_entry)

    def insert_stat_row(self, stat_entry: StatEntry) -> None:
        pin_entry: Optional[PinEntry] = next(
            (pin_entry for pin_entry in self.config_data.pinned
             if pin_entry["type"] == "stat_goal" and pin_entry["app_id"] == self.current_app_id
             and pin_entry["stat_name"] == stat_entry["name"]),
            None,
        )
        pinned_marker: str = "*" if pin_entry else ""
        target_text: str = f"{pin_entry['target']:,}" if pin_entry else ""
        current_value: int = self.stat_values.get(stat_entry["name"], 0)
        self.stats_tree.insert(
            "", tk.END, iid=stat_entry["name"],
            values=(pinned_marker, stat_entry["display_name"], f"{current_value:,}", target_text),
        )

    def insert_achievement_row(self, achievement_entry: AchievementEntry) -> None:
        pin_entry: Optional[PinEntry] = next(
            (pin_entry for pin_entry in self.config_data.pinned
             if pin_entry["type"] == "achievement" and pin_entry["app_id"] == self.current_app_id
             and pin_entry["api_name"] == achievement_entry["api_name"]),
            None,
        )
        pinned_marker: str = "*" if pin_entry else ""
        stat_text: str
        current_text: str
        target_text: str
        if pin_entry and pin_entry.get("stat_name"):
            stat_text = self.get_stat_display_name(pin_entry["stat_name"])
            current_text = f"{self.stat_values.get(pin_entry['stat_name'], 0):,}"
            target_text = f"{pin_entry['target']:,}"
        else:
            stat_text, current_text, target_text = "", "", ""
        self.achievements_tree.insert(
            "", tk.END, iid=achievement_entry["api_name"],
            values=(pinned_marker, achievement_entry["display_name"], achievement_entry["description"], stat_text, current_text, target_text),
        )

    def get_stat_display_name(self, stat_name: str) -> str:
        stat_entry: Optional[StatEntry] = next((entry for entry in self.stats if entry["name"] == stat_name), None)
        return stat_entry["display_name"] if stat_entry else stat_name

    def toggle_pin_achievement(self, event: tk.Event) -> None:
        item_id: str = self.achievements_tree.identify_row(event.y)
        if not item_id:
            return
        achievement_entry: Optional[AchievementEntry] = next(
            (entry for entry in self.achievements if entry["api_name"] == item_id), None
        )
        if achievement_entry is None:
            return
        if self.config_data.is_achievement_pinned(self.current_app_id, item_id):
            self.config_data.unpin_achievement(self.current_app_id, item_id)
            self.config_data.save()
            self.achievements_tree.item(
                item_id, values=("", achievement_entry["display_name"], achievement_entry["description"], "", "", "")
            )
            self.on_change()
            return

        self.config_data.pin_achievement(
            self.current_app_id,
            self.current_game_name,
            achievement_entry["api_name"],
            achievement_entry["display_name"],
            achievement_entry["description"],
        )
        self.config_data.save()
        self.achievements_tree.item(
            item_id, values=("*", achievement_entry["display_name"], achievement_entry["description"], "", "", "")
        )
        self.on_change()

        guessed_stat: Optional[StatEntry] = StatMatcher.guess_stat_for_achievement(achievement_entry, self.stats)
        guessed_target: Optional[int] = StatMatcher.extract_target_number(achievement_entry["description"])
        if guessed_stat is not None and guessed_target is not None:
            current_value: int = self.stat_values.get(guessed_stat["name"], 0)
            self.config_data.link_achievement_stat(self.current_app_id, achievement_entry["api_name"], guessed_stat["name"], guessed_target)
            self.config_data.save()
            self.achievements_tree.item(
                item_id,
                values=(
                    "*", achievement_entry["display_name"], achievement_entry["description"], guessed_stat["display_name"],
                    f"{current_value:,}", f"{guessed_target:,}",
                ),
            )
            self.on_change()
        elif self.stats and messagebox.askyesno(
            "Track progress?",
            f"Track numeric progress for '{achievement_entry['display_name']}' using one of this "
            f"game's stats, instead of just locked/unlocked?",
            parent=self,
        ):
            self.link_stat_to_achievement(achievement_entry)

    def link_stat_to_achievement(self, achievement_entry: AchievementEntry) -> None:
        chosen_stat: Optional[StatEntry] = StatPicker.ask(self, self.stats)
        if chosen_stat is None:
            return
        current_value: int = self.stat_values.get(chosen_stat["name"], 0)
        target_value: Optional[int] = simpledialog.askinteger(
            "Track progress",
            f"Current value of '{chosen_stat['display_name']}': {current_value:,}\n\n"
            f"Track progress toward what target value?",
            parent=self,
            minvalue=1,
        )
        if target_value is None:
            return
        self.config_data.link_achievement_stat(self.current_app_id, achievement_entry["api_name"], chosen_stat["name"], target_value)
        self.config_data.save()
        self.achievements_tree.item(
            achievement_entry["api_name"],
            values=(
                "*", achievement_entry["display_name"], achievement_entry["description"], chosen_stat["display_name"],
                f"{current_value:,}", f"{target_value:,}",
            ),
        )
        self.on_change()

    def toggle_pin_stat(self, event: tk.Event) -> None:
        item_id: str = self.stats_tree.identify_row(event.y)
        if not item_id or self.current_app_id is None:
            return
        stat_entry: Optional[StatEntry] = next((entry for entry in self.stats if entry["name"] == item_id), None)
        if stat_entry is None:
            return

        current_value: int = self.stat_values.get(item_id, 0)
        if self.config_data.is_stat_pinned(self.current_app_id, item_id):
            self.config_data.unpin_stat_goal(self.current_app_id, item_id)
            self.config_data.save()
            self.stats_tree.item(item_id, values=("", stat_entry["display_name"], f"{current_value:,}", ""))
            self.on_change()
            return

        self.ask_target_and_pin_stat(stat_entry, current_value)

    def ask_target_and_pin_stat(self, stat_entry: StatEntry, current_value: int) -> None:
        target_value: Optional[int] = simpledialog.askinteger(
            "Pin as goal",
            f"Current value of '{stat_entry['display_name']}': {current_value:,}\n\n"
            f"Track progress toward what target value?",
            parent=self,
            minvalue=1,
        )
        if target_value is None:
            return
        display_label: Optional[str] = simpledialog.askstring(
            "Pin as goal", "Label to show on the tracker:", parent=self, initialvalue=stat_entry["display_name"]
        )
        if not display_label:
            display_label = stat_entry["display_name"]
        self.config_data.pin_stat_goal(self.current_app_id, self.current_game_name, stat_entry["name"], display_label, target_value)
        self.config_data.save()
        self.stats_tree.item(
            stat_entry["name"], values=("*", stat_entry["display_name"], f"{current_value:,}", f"{target_value:,}")
        )
        self.set_status(f"Pinned goal: {display_label}")
        self.on_change()


class StatPicker(tk.Toplevel):
    @classmethod
    def ask(cls, parent: tk.Misc, stats: list[StatEntry]) -> Optional[StatEntry]:
        dialog: "StatPicker" = cls(parent, stats)
        parent.wait_window(dialog)
        return dialog.result

    def __init__(self, master: tk.Misc, stats: list[StatEntry]) -> None:
        super().__init__(master)
        self.title("Pick a stat")
        self.geometry("300x360")
        self.stats: list[StatEntry] = stats
        self.visible_stats: list[StatEntry] = stats
        self.result: Optional[StatEntry] = None

        body: ttk.Frame = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        self.search_variable: tk.StringVar = tk.StringVar()
        self.search_variable.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(body, textvariable=self.search_variable).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.listbox: tk.Listbox = tk.Listbox(body, exportselection=False)
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.listbox.bind("<Double-1>", lambda event: self.confirm())
        self.apply_filter()

        button_row: ttk.Frame = ttk.Frame(body)
        button_row.grid(row=2, column=0, pady=(8, 0))
        ttk.Button(button_row, text="Select", command=self.confirm).pack(side="left", padx=4)
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

    def apply_filter(self) -> None:
        search_text: str = self.search_variable.get().strip().lower()
        self.listbox.delete(0, tk.END)
        self.visible_stats = [
            stat_entry for stat_entry in self.stats if search_text in stat_entry["display_name"].lower()
        ]
        for stat_entry in self.visible_stats:
            self.listbox.insert(tk.END, stat_entry["display_name"])

    def confirm(self) -> None:
        selection: tuple[int, ...] = self.listbox.curselection()
        if selection:
            self.result = self.visible_stats[selection[0]]
        self.destroy()


class GameLibraryPicker(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        steam_client: SteamClient,
        already_added_app_ids: set[int],
        on_pick: Callable[[list[GameEntry]], None],
    ) -> None:
        super().__init__(master)
        self.title("Add from Library")
        self.geometry("380x480")
        self.steam_client: SteamClient = steam_client
        self.already_added_app_ids: set[int] = already_added_app_ids
        self.on_pick: Callable[[list[GameEntry]], None] = on_pick
        self.games: list[GameEntry] = []
        self.visible_games: list[GameEntry] = []

        body: ttk.Frame = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        self.filter_variable: tk.StringVar = tk.StringVar()
        self.filter_variable.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(body, textvariable=self.filter_variable).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        list_frame: ttk.Frame = ttk.Frame(body)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.listbox: tk.Listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar: ttk.Scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.status_label: ttk.Label = ttk.Label(body, text="Loading your library...", foreground="#a33")
        self.status_label.grid(row=2, column=0, sticky="w", pady=(6, 0))

        button_row: ttk.Frame = ttk.Frame(body)
        button_row.grid(row=3, column=0, sticky="e", pady=(6, 0))
        ttk.Button(button_row, text="Add selected", command=self.add_selected).pack(side="right")
        ttk.Button(button_row, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 6))

        self.grab_set()
        threading.Thread(target=self.load_owned_games, daemon=True).start()

    def load_owned_games(self) -> None:
        try:
            owned_games: list[GameEntry] = self.steam_client.get_owned_games()
        except SteamAPIError as error:
            self.after(0, self.status_label.config, {"text": str(error)})
            return
        self.after(0, self.populate_games, owned_games)

    def populate_games(self, owned_games: list[GameEntry]) -> None:
        self.games = [
            game_entry for game_entry in owned_games if game_entry["app_id"] not in self.already_added_app_ids
        ]
        self.status_label.config(text=f"{len(self.games)} game(s) available.")
        self.apply_filter()

    def apply_filter(self) -> None:
        search_text: str = self.filter_variable.get().strip().lower()
        self.listbox.delete(0, tk.END)
        self.visible_games = [
            game_entry for game_entry in self.games if search_text in game_entry["name"].lower()
        ]
        for game_entry in self.visible_games:
            self.listbox.insert(tk.END, game_entry["name"])

    def add_selected(self) -> None:
        picked_games: list[GameEntry] = [self.visible_games[index] for index in self.listbox.curselection()]
        if not picked_games:
            self.destroy()
            return
        self.destroy()
        self.on_pick(picked_games)
