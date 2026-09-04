import tkinter as tk

from setup_dialog import SetupDialog
from tracker_store import TrackerConfig
from tracker_widget import TrackerWidget


class AchievementTrackerApp:
    def __init__(self) -> None:
        self.config: TrackerConfig = TrackerConfig.load()
        self.root_window: tk.Tk = tk.Tk()
        self.root_window.withdraw()

    def run(self) -> None:
        if not self.config.get("api_key") or not self.config.get("steam_id64"):
            SetupDialog(self.root_window, self.config, self.start_widget)
        else:
            self.start_widget()

        self.root_window.mainloop()

    def start_widget(self) -> None:
        self.root_window.deiconify()
        tracker_widget: TrackerWidget = TrackerWidget(self.root_window, self.config)
        if not self.config["games"]:
            tracker_widget.open_browser()


def main() -> None:
    AchievementTrackerApp().run()


if __name__ == "__main__":
    main()
