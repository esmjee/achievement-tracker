import tkinter as tk
from typing import Callable

from steam_client import SteamClient
from tracker_store import TrackerConfig


class SetupDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, config: TrackerConfig, on_done: Callable[[], None]) -> None:
        super().__init__(master)
        self.title("Achievement Tracker Setup")
        self.resizable(False, False)
        self.on_done: Callable[[], None] = on_done
        self.config_data: TrackerConfig = config

        padding_options: dict[str, int] = {"padx": 10, "pady": 4}

        tk.Label(
            self,
            text=(
                "1. Get a free Steam Web API key:\n"
                "   steamcommunity.com/dev/apikey\n"
                "\n"
                "2. Find your SteamID64:\n"
                "   steamid.io (paste your profile URL)\n\n"
                "Your Steam profile and game details/stats must be\n"
                "set to Public in your Steam privacy settings."
            ),
            justify="left",
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, columnspan=2, **padding_options)

        tk.Label(self, text="Steam Web API key:").grid(row=1, column=0, sticky="e", **padding_options)
        self.api_key_variable: tk.StringVar = tk.StringVar(value=config.get("api_key", ""))
        tk.Entry(self, textvariable=self.api_key_variable, width=40).grid(row=1, column=1, **padding_options)

        tk.Label(self, text="Your SteamID64:").grid(row=2, column=0, sticky="e", **padding_options)
        self.steam_id_variable: tk.StringVar = tk.StringVar(value=config.get("steam_id64", ""))
        tk.Entry(self, textvariable=self.steam_id_variable, width=40).grid(row=2, column=1, **padding_options)

        self.error_label: tk.Label = tk.Label(self, text="", fg="red", font=("Segoe UI", 9))
        self.error_label.grid(row=3, column=0, columnspan=2)

        tk.Button(self, text="Save & Continue", command=self.save).grid(
            row=4, column=0, columnspan=2, pady=(4, 10)
        )

        self.protocol("WM_DELETE_WINDOW", master.destroy)
        self.grab_set()

    def save(self) -> None:
        api_key: str = self.api_key_variable.get().strip()
        steam_id64: str = self.steam_id_variable.get().strip()
        if not api_key or not steam_id64:
            self.error_label.config(text="Both fields are required.")
            return
        self.error_label.config(text="Checking...")
        self.update_idletasks()
        try:
            SteamClient(api_key, steam_id64).verify_credentials()
        except Exception as error:
            self.error_label.config(text=f"Couldn't verify: {error}")
            return
        self.config_data["api_key"] = api_key
        self.config_data["steam_id64"] = steam_id64
        self.config_data.save()
        self.destroy()
        self.on_done()
