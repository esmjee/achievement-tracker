import json
import os
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request

APPID = 648800  # Raft
STAT_NAME = "stat_player_hookCount"
TARGET = 5000
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def fetch_hook_count(api_key, steam_id64):
    params = urllib.parse.urlencode(
        {"appid": APPID, "key": api_key, "steamid": steam_id64}
    )
    url = f"https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    stats = data.get("playerstats", {}).get("stats", [])
    for stat in stats:
        if stat.get("name") == STAT_NAME:
            return int(stat.get("value", 0))
    raise ValueError(f"Stat '{STAT_NAME}' not found in response (has this save file hooked anything yet?)")


class SetupDialog(tk.Toplevel):
    def __init__(self, master, cfg, on_done):
        super().__init__(master)
        self.title("Hook Counter Setup")
        self.resizable(False, False)
        self.on_done = on_done
        self.cfg = cfg

        pad = {"padx": 10, "pady": 4}

        tk.Label(
            self,
            text=(
                "1. Get a free Steam Web API key:\n"
                "   steamcommunity.com/dev/apikey\n"
                "\n"
                "2. Find your SteamID64:\n"
                "   steamid.io (paste your profile URL)\n\n"
                "Your Raft game details/stats must be set to\n"
                "Public on Steam privacy settings."
            ),
            justify="left",
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, columnspan=2, **pad)

        tk.Label(self, text="Steam Web API key:").grid(row=1, column=0, sticky="e", **pad)
        self.api_key_var = tk.StringVar(value=cfg.get("api_key", ""))
        tk.Entry(self, textvariable=self.api_key_var, width=40).grid(row=1, column=1, **pad)

        tk.Label(self, text="Your SteamID64:").grid(row=2, column=0, sticky="e", **pad)
        self.steam_id_var = tk.StringVar(value=cfg.get("steam_id64", ""))
        tk.Entry(self, textvariable=self.steam_id_var, width=40).grid(row=2, column=1, **pad)

        self.error_label = tk.Label(self, text="", fg="red", font=("Segoe UI", 9))
        self.error_label.grid(row=3, column=0, columnspan=2)

        tk.Button(self, text="Save & Start", command=self.save).grid(
            row=4, column=0, columnspan=2, pady=(4, 10)
        )

        self.protocol("WM_DELETE_WINDOW", master.destroy)
        self.grab_set()

    def save(self):
        api_key = self.api_key_var.get().strip()
        steam_id = self.steam_id_var.get().strip()
        if not api_key or not steam_id:
            self.error_label.config(text="Both fields are required.")
            return
        self.error_label.config(text="Checking...")
        self.update_idletasks()
        try:
            fetch_hook_count(api_key, steam_id)
        except Exception as e:  # noqa: BLE001
            self.error_label.config(text=f"Couldn't verify: {e}")
            return
        self.cfg["api_key"] = api_key
        self.cfg["steam_id64"] = steam_id
        save_config(self.cfg)
        self.destroy()
        self.on_done()


class HookCounterWidget:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.poll_seconds = cfg.get("poll_seconds", 60)
        self._drag = {"x": 0, "y": 0}

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#1b1f27")
        root.attributes("-alpha", 0.92)

        x = cfg.get("window_x")
        y = cfg.get("window_y")
        if x is None or y is None:
            x, y = root.winfo_screenwidth() - 240, 40
        root.geometry(f"220x112+{x}+{y}")

        frame = tk.Frame(root, bg="#1b1f27")
        frame.pack(fill="both", expand=True)

        top_bar = tk.Frame(frame, bg="#1b1f27")
        top_bar.pack(fill="x")
        tk.Label(
            top_bar, text="🎣 Expert Gatherer", fg="#9fb4d1", bg="#1b1f27",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=8, pady=(6, 0))
        close_btn = tk.Label(
            top_bar, text="✕", fg="#9fb4d1", bg="#1b1f27", font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        close_btn.pack(side="right", padx=8, pady=(6, 0))
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        self.count_label = tk.Label(
            frame, text="Loading...", fg="#ffffff", bg="#1b1f27", font=("Segoe UI", 18, "bold")
        )
        self.count_label.pack(pady=(2, 0))

        self.status_label = tk.Label(
            frame, text="", fg="#7a8699", bg="#1b1f27", font=("Segoe UI", 8)
        )
        self.status_label.pack()

        self.countdown_label = tk.Label(
            frame, text="", fg="#565f6e", bg="#1b1f27", font=("Segoe UI", 8)
        )
        self.countdown_label.pack()

        drag_widgets = (frame, top_bar, self.count_label, self.status_label, self.countdown_label)
        for widget in drag_widgets:
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)
            widget.bind("<ButtonRelease-1>", self.end_drag)

        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Refresh now", command=self.manual_refresh)
        menu.add_command(label="Edit settings", command=self.open_settings)
        menu.add_separator()
        menu.add_command(label="Quit", command=root.destroy)

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        for widget in drag_widgets:
            widget.bind("<Button-3>", show_menu)

        self._stop = False
        self.remaining = self.poll_seconds
        self.refresh_now()
        self.tick_countdown()

    def start_drag(self, event):
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag["x"])
        y = self.root.winfo_y() + (event.y - self._drag["y"])
        self.root.geometry(f"+{x}+{y}")

    def end_drag(self, event):
        self.cfg["window_x"] = self.root.winfo_x()
        self.cfg["window_y"] = self.root.winfo_y()
        save_config(self.cfg)

    def open_settings(self):
        SetupDialog(self.root, self.cfg, self.refresh_now)

    def refresh_now(self):
        threading.Thread(target=self._poll_once, daemon=True).start()

    def manual_refresh(self):
        self.remaining = self.poll_seconds
        self.refresh_now()

    def tick_countdown(self):
        self.countdown_label.config(text=f"Next check in {self.remaining}s")
        if self.remaining <= 0:
            self.remaining = self.poll_seconds
            self.refresh_now()
        else:
            self.remaining -= 1
        self.root.after(1000, self.tick_countdown)

    def _poll_once(self):
        try:
            count = fetch_hook_count(self.cfg["api_key"], self.cfg["steam_id64"])
            remaining = max(TARGET - count, 0)
            self.root.after(0, self._update_ui, remaining, count, None)
        except Exception as e:  # noqa: BLE001
            self.root.after(0, self._update_ui, None, None, str(e))

    def _update_ui(self, remaining, count, error):
        if error:
            self.count_label.config(text="Error", fg="#e06666")
            self.status_label.config(text=error[:34])
            return
        if remaining == 0:
            self.count_label.config(text="Unlocked! 🎉", fg="#7fd67f")
        else:
            self.count_label.config(text=f"{remaining:,} left", fg="#ffffff")
        self.status_label.config(
            text=f"{count:,} / {TARGET:,} hooked · {time.strftime('%H:%M:%S')}"
        )


def main():
    cfg = load_config()
    root = tk.Tk()
    root.withdraw()

    def start_widget():
        root.deiconify()
        HookCounterWidget(root, cfg)

    if not cfg.get("api_key") or not cfg.get("steam_id64"):
        SetupDialog(root, cfg, start_widget)
    else:
        start_widget()

    root.mainloop()


if __name__ == "__main__":
    main()
